import os
import re
import sys
import time
import requests
import email_sender
from multiprocessing.dummy import Pool
from setting import *

class WeiboSigner:
    MAX_RETRIES = 4  # 最大重试次数

    def __init__(self, gsid):
        self._success_sign = 0
        self._fail_sign = 0
        self._already_sign = 0
        self._fail = False

        self._pool = Pool(100)

        self._headers = {
            'Referer': 'https://m.weibo.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'
        }
        self._cookies = {
            'SUB': gsid
        }

    def keep_cookies_alive(self):
        url = 'https://m.weibo.cn/api/config/list'
        r = requests.get(url, cookies=self._cookies, headers=self._headers)
        if r.json()['ok'] == 1:
            channels = r.json()['data']['channel']
            for ch in channels:
                if ch['name'] == '热门':
                    hot_gid = ch['gid']
            hot_url = 'https://m.weibo.cn/api/container/getIndex?containerid=' + hot_gid
            h_r = requests.get(hot_url, cookies=self._cookies, headers=self._headers)
            # print(h_r.status_code)
            # print(h_r.text)
        frd_url = 'https://m.weibo.cn/feed/friends'
        r = requests.get(frd_url, cookies=self._cookies, headers=self._headers)
        # print(r.status_code)
        # print(r.text)

    def get_sign_list(self):
        info_list = []
        since_id = ''
        while True:
            # https://m.weibo.cn/p/232478_-_bottom_mine_followed
            url = f'https://m.weibo.cn/api/container/getIndex?containerid=100803_-_followsuper&since_id={since_id}'
            r = requests.get(url, cookies=self._cookies, headers=self._headers)
            if r.json()['ok'] != 1:
                try:
                    errno = r.json()['errno']
                except:
                    continue
                if errno == '100005':
                    print(r.json()['msg'])
                    self.wait(600)
                    continue
            self._cookies.update(r.cookies.get_dict())
            cards = r.json()['data']['cards']
            for card in cards:
                if card['card_type'] != '11':
                    continue
                card_group = card['card_group']
                for group in card_group:
                    if group['card_type'] == '8':
                        info = self.extract_info(group)
                        info_list.append(info)
            since_id = r.json()['data']['cardlistInfo']['since_id']
            if not since_id:
                break
        info_list.sort(key=lambda keys: keys['lv'], reverse=True)
        print('*' * 50)
        print(f'爬取完毕共{len(info_list)}个超话')
        print('*' * 50)
        return info_list

    def extract_info(self, group):
        info = {}
        print('*' * 50)
        # 超话名
        title_sub = group['title_sub']
        # 超话等级
        lv = group['desc1']
        # 超话信息
        desc = group['desc2'].strip()
        # 去掉多余换行符
        desc = '\n'.join([i for i in desc.split('\n') if i])
        # 超话签到信息
        sign_info = group['buttons'][0]['name']
        # 超话id
        containerid = group['scheme'].split('&')[0].split('=')[1]
        if sign_info == '签到':
            sign_info = '未签到'
        sign_url = group['buttons'][0]['scheme']
        if sign_url:
            sign_url = 'https://m.weibo.cn' + group['buttons'][0]['scheme']
        info['title_sub'] = title_sub
        info['lv'] = int(re.findall(r'\d+', lv)[0])
        info['desc'] = desc
        info['sign_info'] = sign_info
        info['containerid'] = containerid
        info['sign_url'] = sign_url
        print(title_sub)
        print(lv)
        # if desc != '':
        #     print(desc)
        print(sign_info)
        return info

    def sign(self, args):
        i, info = args
        if info['sign_info'] == '未签到':
            title_sub = info['title_sub']
            sign_url = info['sign_url']
            lv = info['lv']
            retries = 0  # 初始化重试次数
            is_success = False
            while retries < self.MAX_RETRIES:
                try:
                    r = requests.post(sign_url, cookies=self._cookies, headers=self._headers, timeout=3)
                    if r.status_code == 200 and r.json()['ok'] == 1:
                        is_success = True
                        break
                    else:
                        raise Exception
                except:
                    retries += 1  # 增加重试次数
                    if retries >= self.MAX_RETRIES:
                        self._fail = True
                        break
                    wait_time = 2 ** retries  # 指数退避算法
                    time.sleep(wait_time)  # 等待一段时间后重试
            if is_success:
                print(f'第{i}个签到成功："{title_sub}" 等级LV.{lv}')
                self._success_sign += 1
            else:
                print(f'第{i}个签到失败："{title_sub}" 等级LV.{lv}')
                self._fail_sign += 1
        else:
            self._already_sign += 1

    def start_sign(self):
        self._fail = False
        info_list = self.get_sign_list()
        while True:
            self._success_sign = 0
            self._fail_sign = 0
            self._already_sign = 0
            lv_gte_12 = [i for i in info_list if i['lv'] >= 12]
            lv_gte_9 = [i for i in info_list if 9 <= i['lv'] < 12]
            lv_gte_5 = [i for i in info_list if 5 <= i['lv'] < 9]
            lv_lt_5 = [i for i in info_list if i['lv'] < 5]
            self._parallel_sign(lv_gte_12)
            self._parallel_sign(lv_gte_9)
            self._parallel_sign(lv_gte_5)
            self._parallel_sign(lv_lt_5)
            if self._fail:
                self.wait(600)
                self._fail = False
                continue
            break
        if self._success_sign + self._already_sign == len(info_list):
            print('今天你已经全部签到')
        else:
            print(f'签到完毕，共签到成功{self._success_sign}个，签到失败{self._fail_sign}个')
            raise Exception

    def _parallel_sign(self, info_list):
        self._pool.map(self.sign, list(enumerate(info_list)))

    def wait(self, seconds):
        for n in range(seconds, 0, -1):
            time.sleep(1)
            sys.stdout.write(f'\r等待时间：{n}秒')
            sys.stdout.flush()

def main():
    env = os.environ
    gsid_list = env.get('GSID', GSID).split(';')

    failed_list = []
    for i, gsid in enumerate(gsid_list):
        print('#' * 60)
        print(f'用户 {i}')
        try:
            signer = WeiboSigner(gsid=gsid)
            signer.start_sign()
            signer.keep_cookies_alive()
        except Exception as e:
            print(f'用户 {i} 签到失败: {e}')
            failed_list.append(f'用户 {i}')
        print('#' * 60)
        print()

    if failed_list:
        to_list = env.get('TO_LIST', TO_LIST)
        if not isinstance(to_list, list):
            to_list = to_list.split(';')
        mail_usr = env.get('MAIL_USR', MAIL_USR)
        mail_auth = env.get('MAIL_AUTH', MAIL_AUTH)
        smtp_server = env.get('SMTP_SERVER', SMTP_SERVER)
        smtp_port = int(env.get('SMTP_PORT', SMTP_PORT))
        email = email_sender.Email(usr=mail_usr, pwd=mail_auth, smtp_server=smtp_server, smtp_port=smtp_port)
        email.connect()
        email.send(to_list, 'WeiBo Chaohua Sign Failed !', ', '.join(failed_list))
        email.quit()

if __name__ == '__main__':
    main()
