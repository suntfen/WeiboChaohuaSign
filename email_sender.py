import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

class Email(object):
    def __init__(self, usr, pwd, smtp_server, smtp_port, ssl=True):
        self.__usr = usr
        self.__pwd = pwd
        if ssl:
            self.__client = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            self.__client = smtplib.SMTP(smtp_server, smtp_port)
    
    def connect(self):
        print("[{}] {}: login in email server".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), self.__usr))
        if self.__pwd:
            self.__client.login(self.__usr, self.__pwd)
    
    def send(self, to_list, subject, content):
        try:
            msg = MIMEMultipart()
            msg.attach(MIMEText(content,'html','utf-8'))
            msg['Subject'] = subject
            msg['From'] = 'Notification <{}>'.format(self.__usr)
            msg['To'] = ';'.join(to_list)
            self.__client.sendmail(self.__usr, to_list, msg.as_string())
            print("[{}] {}: email notification is sent.".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), self.__usr))
        except smtplib.SMTPException as e:
            print(e)
    
    def quit(self):
        print("[{}] {}: exit email server".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), self.__usr))
        self.__client.quit()
