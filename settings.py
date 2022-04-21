import logging
import json
import requests
from urllib import parse
import os

from requests.exceptions import HTTPError

__all__ = ['log', 'CONFIG', 'req']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')


log = logger = logging


class _Config:
    LOGIN_URL = 'https://ids.chd.edu.cn/authserver/login?service=http://cdjk.chd.edu.cn/healthPunch/index/login'
    INFO_URL = 'https://cdjk.chd.edu.cn/healthPunch/project/jkdk/get'
    LOC_URL = 'https://cdjk.chd.edu.cn/GetAddress/Ip/getAddressByLocation'
    SIGN_URL = 'https://cdjk.chd.edu.cn/healthPunch/project/jkdk/add'
    HOST_URL = 'cdjk.chd.edu.cn'
    ORIGIN_URL = 'https://cdjk.chd.edu.cn'
    REFERER_URL = 'https://cdjk.chd.edu.cn/'
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36'
    
    LONGITUDE = 108.961139
    LATITUDE = 34.237077
    ADDR = '长安大学'


class ProductionConfig(_Config):
    LOG_LEVEL = logging.INFO


class DevelopmentConfig(_Config):
    LOG_LEVEL = logging.DEBUG


class HttpRequest(object):
    @staticmethod
    def to_python(json_str: str):
        return json.loads(json_str)

    @staticmethod
    def to_json(obj):
        return json.dumps(obj, indent=4, ensure_ascii=False)
    
    @staticmethod
    def to_urlencode(obj: dict):
        return parse.urlencode(obj)

    def request(self, method, url, max_retry: int = 2,
            params=None, data=None, json=None, headers=None, **kwargs):
        for i in range(max_retry + 1):
            try:
                s = requests.Session()
                response = s.request(method, url, params=params,
                    data=data, json=json, headers=headers, **kwargs)
            except HTTPError as e:
                log.error(f'HTTP error:\n{e}')
                log.error(f'The NO.{i + 1} request failed, retrying...')
            except KeyError as e:
                log.error(f'Wrong response:\n{e}')
                log.error(f'The NO.{i + 1} request failed, retrying...')
            except Exception as e:
                log.error(f'Unknown error:\n{e}')
                log.error(f'The NO.{i + 1} request failed, retrying...')
            else:
                return response

        raise Exception(f'All {max_retry + 1} HTTP requests failed, die.')
    
req = HttpRequest()

RUN_ENV = os.environ.get('RUN_ENV', 'dev')
if RUN_ENV == 'dev':
    CONFIG = DevelopmentConfig()
else:
    CONFIG = ProductionConfig()

log.basicConfig(level=CONFIG.LOG_LEVEL)


MESSAGE_TEMPLATE = '''
    {today:#^28}
    🔅[{insitute}]{name}
    打卡位置: {position}
    打卡时间: {time}
    打卡结果: {status}
    {end:#^28}'''

CONFIG.MESSAGE_TEMPLATE = MESSAGE_TEMPLATE
