# -*- coding: utf-8 -*-
import requests
import time
import logging
import pickle
import sys
from collections import namedtuple
import lxml.etree

from .exceptions import PasswordError


Term = namedtuple("Term", ["id", "name"])


class SHUer:
    _tokenUpdateAt = 0
    tokenTTL = 1500  # token 存活时间
    startUrl = "http://xk.autoisp.shu.edu.cn:8084"

    HTTP_HEADERS = {
        # dummy user-agent
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/603.1.13 (KHTML, like Gecko) Version/10.1 Safari/603.1.13',
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7"
    }

    def __init__(self, studentCode: str, password: str):
        if len(studentCode) != 8:
            raise ValueError("学号格式错误(%s)。" % (studentCode, ))
        self.studentCode = studentCode
        self.password = password
        self._logger = logging.getLogger(__name__)

    @property
    def token(self):
        """
        自动更新的 token
        :return: ASP.NET_SessionId
        """
        if not hasattr(self, "_token"):
            self._logger.info("get token")
            self.refershToken()

        if (time.time() - self._tokenUpdateAt) > self.tokenTTL:
            self._logger.info("auto refersh token")
            self.refershToken()
        return self._token

    @staticmethod
    def parse_term_id(raw_html):
        """从 /Home/TermIndex 页面内容，提取所有 termid

        :return: [Term(20202, "2020-2021学年冬季学期") ...]
        """
        html = lxml.etree.HTML(raw_html)
        terms = html.xpath("//table/tr[@name='rowterm']")
        result = []
        for term in terms:
            termid = int(term.attrib["value"])
            name = term.xpath("./td/text()")[0].strip()
            result.append(Term(termid, name))
        return result

    def _refershToken(self):
        """刷新或者获取 ASP.NET_SessionId
        """
        self._logger.info("登录中...")
        session = requests.Session()
        session.headers.update(self.HTTP_HEADERS)
        r = session.get(self.startUrl)

        request_url = r.url
        if not request_url.startswith("https://oauth.shu.edu.cn/login"):
            raise RuntimeError(1, f"unexpected request_url: {request_url}")

        request_data = {
            "username": self.studentCode,
            "password": self.password,
            "login_submit": ""
        }
        session.headers.update({
            "referer": request_url
        })

        r = session.post(request_url, request_data)
        if "认证失败" in r.text:
            self._logger.critical("密码错误，登录失败")
            raise PasswordError

        # 选择学期页面
        term_index_url = r.url
        if not term_index_url.endswith("/Home/TermIndex"):
            raise RuntimeError(
                2, f"unexpected term_index_url: {term_index_url}")

        # TODO: 询问用户选择学期，记住上次的选择
        term = self.parse_term_id(r.text)[0]
        self._logger.info("自动选择了 %s", term.name)

        request_url = term_index_url.rsplit("/", 1)[0] + "/TermSelect"
        self._logger.debug("term select request url: %s", request_url)

        r = session.post(request_url, {"termId": term.id})

        if "姓名：" in r.text:
            self._token = session.cookies.get(name="ASP.NET_SessionId")
            self._tokenUpdateAt = time.time()
        else:
            self._logger.critical("登录失败：%s", r.text)
            raise RuntimeError(4, "登录失败")

    def refershToken(self):
        """本函数会失败自动重试
        """
        for _ in range(5):
            try:
                self._refershToken()
                return
            except RuntimeError as e:
                self._logger.error(f"出错：{e}, 正在重试...")
            except requests.exceptions.RequestException as e:
                self._logger.error(f"出错：{e}, 正在重试...")
            time.sleep(3)
        raise RuntimeError("登录失败")

    def dump_to(self, path):
        with open(path, "wb") as file:
            pickle.dump(self, file)

    @ staticmethod
    def from_file(path):
        with open(path, "rb") as file:
            return pickle.load(file)
