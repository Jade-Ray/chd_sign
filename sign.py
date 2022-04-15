import time
import os

from settings import log, CONFIG, req
from notify import Notify


def version():
    return 'v0.0.01'


class Base(object):
    def __init__(self, token: str = None):
        if not isinstance(token, str):
            raise TypeError('%s want a %s but got %s' %
                            (self.__class__, type(__name__), type(token)))
        self._token = token
        
    def get_header(self):
        header = {
            'User-Agent': CONFIG.USER_AGENT,
            'Host': CONFIG.HOST_URL,
            'Origin': CONFIG.ORIGIN_URL,
            'Referer': CONFIG.REFERER_URL,
            'Accept-Encoding': 'gzip, deflate, br',
        }
        return header


class Sign(Base):
    def __init__(self, token: str = None):
        super(Sign, self).__init__(token)
    
    @property
    def message(self):
        return CONFIG.MESSAGE_TEMPLATE
    
    def get_params(self):
        params = {'token': self._token}
        return params
    
    def get_location_params(self):
        params = {'lon': CONFIG.LONGITUDE, 'lat': CONFIG.LATITUDE}
        return params
    
    def get_header(self):
        header = super(Sign, self).get_header()
        header.update({
            'Authorization':self._token,
            'Content-Type':'application/x-www-form-urlencoded',
        })
        return header
    
    def get_location(self):
        log.info('🧭准备获取位置信息...')
        
        try:
            content = req.request(
                'get', CONFIG.LOC_URL, params=self.get_location_params(), headers=self.get_header()).text
            code, msg = req.to_python(content)['code'], req.to_python(content)['msg']
        except Exception as e:
            raise Exception(e)
        
        if code != 200:
            raise Exception(f'Get Loc Info Failed, with {code} code and {msg} msg')
        loc_dict = req.to_python(content)['data']
        log.info(f'位置信息获取完毕, {loc_dict["result"]["ad_info"]["name"]}')
        return loc_dict
    
    def get_info(self):
        log.info('准备获取打卡信息...')
        
        try:
            req.request('get', CONFIG.ORIGIN_URL, params=self.get_params(), headers=self.get_header())
            
            content = req.request(
                'post', CONFIG.INFO_URL, params=self.get_params(), headers=self.get_header()).text
            code, msg = req.to_python(content)['code'], req.to_python(content)['msg']
        except Exception as e:
            raise Exception(e)

        if code != 200:
            raise Exception(f'Get Info Failed, with {code} code and {msg} msg')
        info_dict = req.to_python(content)['data']
        log.info(f'打卡信息获取完毕, {info_dict["szyx"]} {info_dict["xm"]} 的健康打卡')
        return info_dict
        
    def run(self):
        message_list = []
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
                'post', CONFIG.SIGN_URL, headers=self.get_header(),
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
    
    # TOKEN: CHD用户TOKEN.多个账号的COOKIE值之间用 # 号隔开,例如: 1#2#3#4
    # LON: 定位经度，默认为长安大学经度
    # LAT: 定位纬度，默认为长安大学纬度
    # ADDR: 定位地址，默认为长安大学
    TOKEN = ''
    
    if os.environ.get('TOKEN', '') != '':
        TOKEN = os.environ['TOKEN']
    if os.environ.get('LON', '') != '':
        CONFIG.LONGITUDE = os.environ['LON']
    if os.environ.get('LAT', '') != '':
        CONFIG.LATITUDE = os.environ['LAT']
    if os.environ.get('ADDR', '') != '':
        CONFIG.ADDR = os.environ['ADDR']
        
    token_list = TOKEN.split('#')
    log.info(f'检测到共配置了 {len(token_list)} 个帐号')
    for i in range(len(token_list)):
        log.info(f'准备为 NO.{i + 1} 账号签到...')
        log.info(f'NO.{i + 1} 账号的TOKEN: {token_list[i]} ')
        try:
            msg = f'	NO.{i + 1} 账号:{Sign(token_list[i]).run()}'
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