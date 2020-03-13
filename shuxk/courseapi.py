# -*- coding: utf-8 -*-
from .models import SHUer
import requests
import logging
import lxml.etree
from collections import namedtuple


class CannotJudgeError(Exception):
    pass


class CourseAPI:
    mainUrl = "http://xk.autoisp.shu.edu.cn"

    def __init__(self, shuer: SHUer):
        """:shuer: SHUer
        """
        self.shuer = shuer
        self.HTTP_HEADERS = shuer.HTTP_HEADERS
        self._logger = logging.getLogger(__name__)
        self._session = requests.Session()
        self._session.headers.update(self.HTTP_HEADERS)

    def resolve_url(self, path):
        if self.mainUrl.endswith("/"):
            request_url = self.mainUrl[:-1] + path
        else:
            request_url = self.mainUrl + path
        return request_url

    def http_request(self, path, method="GET", params=None, data=None):
        """http request with auth.(default: GET)
        """
        request_url = self.resolve_url(path)
        session = self._session
        session.cookies.set("ASP.NET_SessionId", self.shuer.token)
        request_method = getattr(session, method.lower())
        self._logger.debug(f"http {method}: {path}")
        r = request_method(request_url, params=params, data=data)
        return r

    def http_get(self, path, params=None):
        """http GET with auth.
        """
        return self.http_request(path, params=params)

    def http_post(self, path, data=None):
        """http POST with auth.
        """
        return self.http_request(path, method="POST", data=data)

    def is_select_time(self, autoRetry=True):
        try:
            r = self.http_get("/CourseSelectionStudent/FastInput")
        except requests.exceptions.RequestException as e:
            self._logger.error(f"出错：{e}")
            raise CannotJudgeError
        if "选课时间未到" in r.text:
            return False
        elif "英语等级" in r.text:
            return True
        elif autoRetry:
            self._logger.warn("疑似 Token 失效, 自动更新中...")
            self.shuer.refershToken()
            return self.is_select_time(autoRetry=False)
        else:
            raise CannotJudgeError

    def get_course_info(self, courseSeq, teacherSeq):
        params = {
            "CourseNo": courseSeq,
            "TeachNo": teacherSeq,
            "CourseName": "",
            "TeachName": "",
            "CourseTime": "",
            "NotFull": False,
            "Credit": "",
            "Campus": 0,
            "Enrolls": "",
            "DataCount": 0,
            "MinCapacity": "",
            "MaxCapacity": "",
            "PageIndex": 1,
            "PageSize": 20,
            "FunctionString": "InitPage"
        }
        r = self.http_get("/StudentQuery/CtrlViewQueryCourse", params)
        html = lxml.etree.HTML(r.text)
        td = html.xpath("//table[@class='tbllist']/tr/td")
        self._logger.debug(f"GetCourseInfo: td length={len(td)}")
        CourseInfo = namedtuple(
            "CourseInfo", ["courseName", "teacherName", "capacity", "studentNum", "credit"])
        return CourseInfo(
            courseName=td[1].text.strip(),
            credit=int(td[2].text.strip()),
            teacherName=td[4].text.strip(),
            capacity=int(td[7].text.strip()),
            studentNum=int(td[8].text.strip())
        )

    def select_course(self, courses):
        if len(courses) > 6:
            self._logger.warn(f"单次选课数量(当前：{len(courses)})应小于等于6. 已忽略多余的。")
        if len(courses) == 0:
            self._logger.warn(f"没有待选课程")
            return True
        data = {
            "IgnorClassMark": "False",
            "IgnorCourseGroup": "False",
            "IgnorCredit": "False",
            "StudentNo": self.shuer.studentCode,
            'ListCourse[0].CID': "",
            'ListCourse[0].TNo': "",
            'ListCourse[0].NeedBook': 'false'
        }
        for i, c in enumerate(courses):
            courseSeq = c[0]
            teacherSeq = c[1]
            data["ListCourse[%d].CID" % i] = courseSeq
            data["ListCourse[%d].TNo" % i] = teacherSeq
            data["ListCourse[%d].NeedBook" % i] = "false"

        for i in range(1 + i, 6):
            data["ListCourse[%d].CID" % i] = ""
            data["ListCourse[%d].TNo" % i] = ""
            data["ListCourse[%d].NeedBook" % i] = "false"
        if not self.is_select_time():
            self._logger.error("现在不是选课时间")
            return False
        r = self.http_post(
            "/CourseSelectionStudent/CtrlViewOperationResult", data=data)
        # 由于写代码时选课系统未开放， 所以无法自动判断是否成功。
        # 临时方案
        # TODO
        import pathlib
        output_path = pathlib.Path("result.html").resolve()
        with output_path.open("w", encoding="utf-8") as file:
            file.write(r.text)
        print(f"选课结果已输出至：{str(output_path)}")
        return True
