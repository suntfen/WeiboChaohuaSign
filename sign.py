import os
import re
import sys
import time
import requests
import email_sender
from multiprocessing.dummy import Pool
from setting import *

pool = Pool(100)

def get_sign_list():
    cookies = {'SUB': gsid,
    'user-agent': 'Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Mobile Safari/537.36'}
    info_list = []
    since_id = ''
    s = 0
    while True:
        url = 'https://m.weibo.cn/api/container/getIndex?containerid=100803_-_followsuper&since_id=' + since_id
        # 获取超话列表
        r = requests.get(url, cookies=cookies, )
        if r.json()['ok'] != 1:
            try:
                errno = r.json()['errno']
            except:
                continue
            if errno == '100005':
                print(r.json()['msg'])
                n = 600
                while n + 1:
                    time.sleep(1)
                    sys.stdout.write(f'\r等待时间：{n}秒')
                    n -= 1
                continue
        c = cookies
        c.update(r.cookies.get_dict())
        cards = r.json()['data']['cards']
        for i in range(len(cards)):
            card_type = cards[i]['card_type']
            if card_type != '11':
                continue
            card_group = cards[i]['card_group']
            for j in range(len(card_group)):
                if card_group[j]['card_type'] == '8':
                    info = {}
                    print('*' * 50)
                    # 超话名
                    title_sub = card_group[j]['title_sub']
                    # 超话等级
                    lv = card_group[j]['desc1']
                    # 超话信息
                    desc = card_group[j]['desc2'].strip()
                    # 去掉多余换行符
                    desc = '\n'.join([i for i in desc.split('\n') if i != ''])
                    # 超话签到信息
                    sign_info = card_group[j]['buttons'][0]['name']
                    # 超话id
                    containerid = card_group[j]['scheme'].split('&')[0].split('=')[1]
                    if sign_info == '签到':
                        sign_info = '未签到'
                    sign_url = card_group[j]['buttons'][0]['scheme']
                    if sign_url:
                        sign_url = 'https://m.weibo.cn' + card_group[j]['buttons'][0]['scheme']
                    info['title_sub'] = title_sub
                    info['lv'] = int(re.findall('\d+', lv)[0])
                    info['desc'] = desc
                    info['sign_info'] = sign_info
                    info['containerid'] = containerid
                    info['sign_url'] = sign_url
                    info['cookies'] = c
                    print(title_sub)
                    print(lv)
                    # if desc != '':
                    #     print(desc)
                    print(sign_info)
                    info_list.append(info)
                    s += 1
        # 获取下一页id
        since_id = r.json()['data']['cardlistInfo']['since_id']
        # 获取到空就是爬取完了
        if since_id == '' or since_id == '0':
            break
    # 按等级从大到小排序超话
    info_list.sort(key=lambda keys: keys['lv'], reverse=True)
    print('*' * 50)
    print('爬取完毕共%d个超话' % s)
    print('*' * 50)
    return info_list


def sign(args):
    global success_sign
    global fail_sign
    global already_sign
    global fail
    i, info = args
    if info['sign_info'] == '未签到':
        title_sub = info['title_sub']
        sign_url = info['sign_url']
        cookies = info['cookies']
        lv = info['lv']
        n = 1
        while True:
            try:
                r = requests.post(sign_url, cookies=cookies, headers={
                    'Referer': 'https://m.weibo.cn',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'},
                                  timeout=3)
                if r.status_code == 200:
                    break
                else:
                    raise Exception
            except:
                if n >= 16:
                    fail = True
                    return False
                n *= 2
                time.sleep(1)
        if r.json()['ok'] == 1:
            print(f'第{i}个签到成功："{title_sub}" 等级LV.{lv}')
            success_sign += 1
        else:
            print(f'第{i}个签到失败："{title_sub}" 等级LV.{lv}')
            fail_sign += 1
    else:
        already_sign += 1


def start_sign():
    global success_sign
    global fail_sign
    global already_sign
    global fail
    fail = False
    info_list = get_sign_list()
    while True:
        success_sign = 0
        fail_sign = 0
        already_sign = 0
        lv_gte_12 = [i for i in info_list if i['lv'] >= 12]
        lv_gte_9 = [i for i in info_list if 9 <= i['lv'] < 12]
        lv_gte_5 = [i for i in info_list if 5 <= i['lv'] < 9]
        lv_lt_5 = [i for i in info_list if i['lv'] < 5]
        pool.map(sign, list(enumerate(lv_gte_12)))
        pool.map(sign, list(enumerate(lv_gte_9)))
        pool.map(sign, list(enumerate(lv_gte_5)))
        pool.map(sign, list(enumerate(lv_lt_5)))
        if fail:
            n = 600
            while n + 1:
                time.sleep(1)
                sys.stdout.write(f'\r等待时间：{n}秒')
                n -= 1
            fail = False
            continue
        break
    if success_sign + already_sign == len(info_list):
        print('今天你已经全部签到')
    else:
        print(f'签到完毕，共签到成功{success_sign}个，签到失败{fail_sign}个')


if __name__ == '__main__':
    env = os.environ
    if 'TO_LIST' in env.keys() and env['TO_LIST']:
        to_list = env['TO_LIST'].split(';')
    else:
        to_list = TO_LIST

    if 'MAIL_USR' in env.keys() and env['MAIL_USR']:
        mail_usr = env['MAIL_USR']
    else:
        mail_usr = MAIL_USR

    if 'MAIL_AUTH' in env.keys() and env['MAIL_AUTH']:
        mail_auth = env['MAIL_AUTH']
    else:
        mail_auth = MAIL_AUTH

    if 'SMTP_SERVER' in env.keys() and env['SMTP_SERVER']:
        smtp_server = env['SMTP_SERVER']
    else:
        smtp_server = SMTP_SERVER

    if 'SMTP_PORT' in env.keys() and env['SMTP_PORT']:
        smtp_port = env['SMTP_PORT']
    else:
        smtp_port = int(SMTP_PORT)

    if 'GSID' in env.keys() and env['GSID']:
        gsid_list = env['GSID'].split(';')
    else:
        gsid_list = GSID.split(';')

    failed_list = []
    for i, id in enumerate(gsid_list):
        print('#' * 60)
        print('用户 {}'.format(i))
        try:
            gsid = id
            start_sign()
        except:
            print('用户 {} 签到失败'.format(i))
            failed_list.append('用户 {}'.format(i))
        print('#' * 60)
        print()

    if len(failed_list) > 0:
        email = email_sender.Email(mail_usr, mail_auth, smtp_server, smtp_port)
        email.connect()
        email.send(to_list, 'WeiBo Chaohua Sign Failed !'.format(i), ', '.join(failed_list))
        email.quit()
