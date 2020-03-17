# -*- coding: utf-8 -*-
import requests
import time
import logging
import pickle
import sys


class SHUer:
    _tokenUpdateAt = 0
    tokenTTL = 1500 # seconds
    startUrl = "http://xk.autoisp.shu.edu.cn"

    HTTP_HEADERS = {
        # dummy user-agent
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/603.1.13 (KHTML, like Gecko) Version/10.1 Safari/603.1.13',
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7"
    }

    def __init__(self, studentCode, password):
        if not (isinstance(studentCode, int) and len(str(studentCode)) == 8):
            raise ValueError("学号格式错误(%s)。" % (studentCode, ))
        self.studentCode = studentCode
        self.password = password
        self._logger = logging.getLogger(__name__)

    @property
    def token(self):
        """ASP.NET_SessionId
        """
        if not hasattr(self, "_token"):
            self._logger.info("get token")
            self.refershToken()

        if (time.time() - self._tokenUpdateAt) > self.tokenTTL:
            self._logger.info("auto refersh token")
            self.refershToken()
        return self._token

    def _refershToken(self):
        """刷新或者获取 ASP.NET_SessionId
        """
        session = requests.Session()
        session.headers.update(self.HTTP_HEADERS)
        r = session.get(self.startUrl)

        request_url = r.url
        if "https://oauth.shu.edu.cn/login" != request_url:
            raise RuntimeError(1, f"unexpected request_url: {request_url}")
        
        request_data = {
            "username": self.studentCode,
            "password": self.password,
            "login_submit": "登录/Login"
        }
        session.headers.update({
            "referer": "https://oauth.shu.edu.cn/login"
        })
        
        r = session.post(request_url, request_data)
        if "认证失败" in r.text:
            self._logger.critical("密码错误，登录失败")
            raise RuntimeError(3, "密码错误")

        home_url = r.url
        if not home_url.endswith("/Home/StudentIndex"):
            raise RuntimeError(2, f"unexpected home_url: {home_url}")

        self._token = session.cookies.get(name="ASP.NET_SessionId")
        self._tokenUpdateAt = time.time()

    def refershToken(self):
        for _ in range(10):
            try:
                self._refershToken()
                break
            except RuntimeError as e:
                if e.args[0] == 3:
                    # 密码错误
                    raise
                self._logger.error(f"出错：{e}, 正在重试...")
            except requests.exceptions.RequestException as e:
                self._logger.error(f"出错：{e}, 正在重试...")
            time.sleep(1)

    def dump_to(self, path):
        with open(path, "wb") as file:
            pickle.dump(self, file)

    @staticmethod
    def from_file(path):
        with open(path, "rb") as file:
            return pickle.load(file)
