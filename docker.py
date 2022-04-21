import datetime
import os
import signal
import time
from settings import *

from crontab import CronTab

time_format = "%Y-%m-%d %H:%M:%S"


def stop_me(_signo, _stack):
    log.info("Docker container has stoped....")
    exit(-1)


def main():
    signal.signal(signal.SIGINT, stop_me) # 连接中断
    log.info("使用DOCKER运行CHD健康打卡")
    env = os.environ
    cron_signin = env["CRON_SIGNIN"]
    cron = CronTab(cron_signin, loop=True, random_seconds=True)

    def next_run_time():
        nt = datetime.datetime.now().strftime(time_format)
        delayt = cron.next(default_utc=False)
        nextrun = datetime.datetime.now() + datetime.timedelta(seconds=delayt)
        nextruntime = nextrun.strftime(time_format)
        log.info(f"Current running datetime: {nt}")
        log.info(f"Next run datetime: {nextruntime}")

    def sign():
        hour = datetime.datetime.now().hour
        if hour < 7 or hour >= 20:
            log.info("Schedule time should be between 7:00 to 20:00.")
            return
        log.info("Starting signing")
        os.system("python3 ./sign.py")

    sign()
    next_run_time()
    while True:
        ct = cron.next(default_utc=False)
        time.sleep(ct)
        sign()
        next_run_time()


if __name__ == '__main__':
    main()
