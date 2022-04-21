import os
import time

from urllib import parse
from settings import log, req


class Notify(object):
    """Push all in one
    Param:
        SCKEY: Server酱的SCKEY.详见文档: https://sct.ftqq.com/
    """
    # Github Actions用户请到Repo的Settings->Secrets里设置变量,变量名字必须与上述参数变量名字完全一致,否则无效!!!
    # Name=<变量名字>,Value=<获取的值>
    # Server Chan
    SCKEY = ''
    
    def pushTemplate(self, method, url, params=None, data=None, json=None, headers=None, **kwargs):
        name = kwargs.get('name')
        # needs = kwargs.get('needs')
        token = kwargs.get('token')
        text = kwargs.get('text')
        code = kwargs.get('code')
        if not token:
            log.info(f'{name} 🚫')
            # log.info(f'{name} 推送所需的 {needs} 未设置, 正在跳过...')
            return
        try:
            response = req.to_python(req.request(
                method, url, 2, params, data, json, headers).text)
            if name == 'Server酱':
                rspData = response["data"]
                rspcode = rspData[text]
            else:
                rspcode = response[text]
        except Exception as e:
            # 🚫: disabled; 🥳:success; 😳:fail
            log.error(f'{name} 😳\n{e}')
        else:
            if rspcode == code:
                log.info(f'{name} 🥳')
            # Telegram Bot
            elif name == 'Telegram Bot' and rspcode:
                log.info(f'{name} 🥳')
            elif name == 'Telegram Bot' and response[code] == 400:
                log.error(f'{name} 😳\n请主动给 bot 发送一条消息并检查 TG_USER_ID 是否正确')
            else:
                log.error(f'{name} 😳\n{response}')

    def serverChan(self, text, status, desp):
        SCKEY = self.SCKEY
        if 'SCKEY' in os.environ:
            SCKEY = os.environ['SCKEY']

        url = f'https://sctapi.ftqq.com/{SCKEY}.send'
        data = {
            'text': f'{text} {status}',
            'desp': desp
        }
        conf = ['Server酱', 'SCKEY', SCKEY, 'errno', 0]
        name, needs, token, text, code  = conf

        return self.pushTemplate('post', url, data=data, name=name, needs=needs, token=token, text=text, code=code)
    
    def send(self, **kwargs):
        app = 'CHD打卡小助手'
        status = kwargs.get('status', '')
        msg = kwargs.get('msg', '')
        hide = kwargs.get('hide', '')
        if isinstance(msg, list) or isinstance(msg, dict):
            # msg = self.to_json(msg)
            msg = '\n\n'.join(msg)
        if not hide:
            log.info(f'打卡结果: {status}\n\n{msg}')
        log.info('准备推送通知...')

        self.serverChan(app, status, msg)
        
if __name__ == '__main__':
    Notify().send(app='CHD打卡小助手', status='打卡状态', msg='内容详情')