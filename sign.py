import time
import os

from settings import log, CONFIG, req
from notify import Notify


def version():
    return 'v0.0.02'


class Base(object):
    def __init__(self, cookie: str = None):
        if not isinstance(cookie, str):
            raise TypeError('%s want a %s but got %s' %
                            (self.__class__, type(__name__), type(cookie)))
        self._cookie = cookie
        self._login_num = 0
    
    @property
    def login_num(self):
        self._login_num += 1
        return self._login_num
    
    @property
    def token(self):
        if '_token' in self.__dict__:
            return self._token
        else:
            if self.login_num > 6:
                raise ValueError('超过5次登录失败, 请检查参数!')
            log.info(f'Token 失效, 第{self.login_num}次重新登录')
            self.login()
    
    @token.setter
    def token(self, token):
        if isinstance(token, str):
            self._token = token
        else:
            raise ValueError(f'{token} is not a string')
    
    @property
    def header(self):
        return {
            'User-Agent': CONFIG.USER_AGENT,
            'Host': CONFIG.HOST_URL,
            'Origin': CONFIG.ORIGIN_URL,
            'Referer': CONFIG.REFERER_URL,
            'Accept-Encoding': 'gzip, deflate, br',
        }
        
    def login(self):
        raise NotImplementedError


class Sign(Base):
    def __init__(self, cookie: str = None):
        super(Sign, self).__init__(cookie)
    
    @property
    def message(self):
        return CONFIG.MESSAGE_TEMPLATE
    
    @property
    def token_param(self):
        return {'token': self.token}
    
    @property
    def loc_param(self):
        return {'lon': CONFIG.LONGITUDE, 'lat': CONFIG.LATITUDE}
    
    @property
    def commen_header(self):
        header = self.header
        header.update({
            'Authorization':self.token,
            'Content-Type':'application/x-www-form-urlencoded', # for sign post request
        })
        return header
    
    @property
    def login_header(self):
        header = self.header
        header.update({
            'Host': 'ids.chd.edu.cn',
            'Cookie': self._cookie,
        })
        return header
    
    def login(self):
        log.info('✏️ 准备登录中...')
        try:
            response = req.request('get', CONFIG.LOGIN_URL, headers=self.login_header)
            if response.status_code != 200:
                raise Exception(f'Can not login, with {response.status_code} status code')
            token_param = response.url.split('?')[-1]
            assert 'token' in token_param, '无效或过时Cookie, 请检查Cookie!'
            self.token = token_param.split('=')[-1]
        except Exception as e:
            raise Exception(e)
        log.info('登录成功')
    
    def get_info(self):
        log.info('📄准备获取打卡信息...')
        try:
            content = req.request(
                'post', CONFIG.INFO_URL, params=self.token_param, headers=self.commen_header).text
            code, msg = req.to_python(content)['code'], req.to_python(content)['msg']
            if code != 200:
                raise Exception(f'Get Info Failed, with {code} status code and {msg} msg')
        except Exception as e:
            raise Exception(e)

        info_dict = req.to_python(content)['data']
        log.info(f'打卡信息获取完毕, {info_dict["szyx"]} {info_dict["xm"]} 的健康打卡')
        return info_dict
    
    def get_location(self):
        log.info('🧭准备获取位置信息...')
        try:
            content = req.request(
                'get', CONFIG.LOC_URL, params=self.loc_param, headers=self.commen_header).text
            code, msg = req.to_python(content)['code'], req.to_python(content)['msg']
            if code != 200:
                raise Exception(f'Get Loc Info Failed, with {code} status code and {msg} msg')
        except Exception as e:
            raise Exception(e)
        
        loc_dict = req.to_python(content)['data']
        log.info(f'位置信息获取完毕, {loc_dict["result"]["ad_info"]["name"]}')
        return loc_dict
        
    def run(self):
        message_list = []
        self.login()
        info_dict = self.get_info()
        loc_dict = self.get_location()
        info_dict.update({
            'szdd4': loc_dict["result"]["ad_info"]["name"].replace(',', ''),
            'xxdz41': CONFIG.ADDR,
            'jingdu': loc_dict["result"]["location"]["lng"],
            'weidu': loc_dict["result"]["location"]["lat"],
            'guo': loc_dict["result"]["address_component"]["nation"],
            'sheng': loc_dict["result"]["address_component"]["province"],
            'shi': loc_dict["result"]["address_component"]["city"],
        })
        info_dict = {k: v if v is not None else '' for k, v in info_dict.items()}
        
        log.info('健康打卡中...')
        time.sleep(10)
        message = {
            'today': info_dict['jrrq1'],
            'insitute': info_dict['szyx'],
            'name': info_dict['xm'],
            'position': info_dict['szdd4'],
            'time': time.asctime().split()[3],
            'end': '',
        }
        
        try:
            response = req.to_python(req.request(
                'post', CONFIG.SIGN_URL, headers=self.commen_header,
                data=req.to_urlencode(info_dict)).text)
        except Exception as e:
            raise Exception(e)
        
        if response['code'] != 200:
            message_list.append(response)

        message['status'] = response['msg']
        message_list.append(self.message.format(**message))
        
        log.info("打卡完毕")
        
        return ''.join(message_list)


if __name__ == '__main__':
    log.info(f'🔱CHD 每日健康打卡小助手 {version()}')
    log.info('若打卡失败, 请尝试更新!')
    log.info('任务开始')
    notify = Notify()
    msg_list = []
    ret = success_num = fail_num = 0
    
    # COOKIE: CHD用户COOKIE.多个账号的COOKIE值之间用 # 号隔开,例如: 1#2#3#4
    # LON: 定位经度，默认为长安大学经度
    # LAT: 定位纬度，默认为长安大学纬度
    # ADDR: 定位地址，默认为长安大学
    COOKIE = ''
    
    if os.environ.get('COOKIE', '') != '':
        COOKIE = os.environ['COOKIE']
    if os.environ.get('LON', '') != '':
        CONFIG.LONGITUDE = os.environ['LON']
    if os.environ.get('LAT', '') != '':
        CONFIG.LATITUDE = os.environ['LAT']
    if os.environ.get('ADDR', '') != '':
        CONFIG.ADDR = os.environ['ADDR']

    cookie_list = COOKIE.split('#')
    log.info(f'检测到共配置了 {len(cookie_list)} 个帐号')
    for i in range(len(cookie_list)):
        log.info(f'准备为 NO.{i + 1} 账号签到...')
        log.info(f'NO.{i + 1} 账号的COOKIE: {cookie_list[i]} ')
        try:
            msg = f'	NO.{i + 1} 账号:{Sign(cookie_list[i]).run()}'
            msg_list.append(msg)
            success_num = success_num + 1
        except Exception as e:
            msg = f'	NO.{i + 1} 账号:\n    {e}'
            msg_list.append(msg)
            fail_num = fail_num + 1
            log.error(msg)
            ret = -1
        continue
    notify.send(status=f'成功: {success_num} | 失败: {fail_num}', msg=msg_list)
    if ret != 0:
        log.error('异常退出')
        exit(ret)
    log.info('任务结束')