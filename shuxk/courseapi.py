# -*- coding: utf-8 -*-
from .models import SHUer
import requests
import logging
import lxml.etree
import time
from collections import namedtuple

from .exceptions import CannotJudgeError


SelectCourseResult = namedtuple("SelectCourseResult", [
    "courseSeq", "courseName", "teacherSeq", "teacherName", "failedCause", "success"
])
CourseInfo = namedtuple("CourseInfo", [
    "courseName", "teacherName", "capacity", "studentNum", "credit", "selectRestrict"
])


class CourseAPI:
    mainUrl = "http://xk.autoisp.shu.edu.cn:8084"
    _session: requests.sessions.Session

    HTTP_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/603.1.13 (KHTML, like Gecko) Version/10.1 Safari/603.1.13',
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7"
    }

    def __init__(self, studentCode, token):
        self._token = token
        self.studentCode = studentCode
        self._logger = logging.getLogger(__name__)
        self._session = requests.Session()
        self._session.headers.update(self.HTTP_HEADERS)

    def resolve_url(self, path):
        """选课系统每学期的端口号都不一样，例如：http://xk.autoisp.shu.edu.cn:8084。
        本函数可根据 mainUrl 返回合适的 request_url
        """
        if self.mainUrl.endswith("/"):
            request_url = self.mainUrl[:-1] + path
        else:
            request_url = self.mainUrl + path
        return request_url

    def http_request(self, path, method="GET", params=None, data=None) -> requests.models.Response:
        """http request with auth.(default: GET)
        """
        request_url = self.resolve_url(path)
        session = self._session
        session.cookies.set("ASP.NET_SessionId", self._token)
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

    def in_select_time(self, autoRetry=True):
        """判断是否在选课时间
        """
        try:
            r = self.http_get("/CourseSelectionStudent/FastInput")
        except requests.exceptions.RequestException as e:
            self._logger.error(f"出错：{e}")
            raise CannotJudgeError
        if "选课时间未到" in r.text:
            return False
        elif "英语等级" in r.text:
            return True
        else:
            self._logger.warning("疑似 Token 失效: %s", r.text)
            # self.shuer.refershToken()
            # TODO

    def get_course_info(self, courseSeq, teacherSeq):
        """获取课程信息
        :courseSeq: 课程号
        :teacherSeq: 教师号

        :result: [CourseInfo(), ...]
        """
        params = {
            "PageIndex": 1,
            "PageSize": 30,
            "FunctionString": "Query",
            "CID": courseSeq,
            "CourseName": "",
            "IsNotFull": "false",
            "CourseType": "B",
            "TeachNo": teacherSeq,
            "TeachName": "",
            "Enrolls": "",
            "Capacity1": "",
            "Capacity2": "",
            "CampusId": "",
            "CollegeId": "",
            "Credit": "",
            "TimeText": ""
        }
        r = self.http_get("/StudentQuery/QueryCourseList", params)
        html = lxml.etree.HTML(r.text)
        td = html.xpath("//table[@class='tbllist']/tr/td")
        self._logger.debug(f"GetCourseInfo: td length={len(td)},")
        return CourseInfo(
            courseName=td[1].text.strip(),
            credit=int(td[2].text.strip()),
            teacherName=td[4].xpath("./span/text()")[0],
            capacity=int(td[7].text.strip()),
            studentNum=int(td[8].text.strip()),
            selectRestrict=td[10].text.strip() if td[10].text else ""
        )

    def select_course(self, courses):
        """选课
        :courses: List[Tuple(courseSeq, teacherSeq), ...]
        """
        if len(courses) > 8:
            self._logger.warn(f"单次选课数量(当前：{len(courses)})应小于等于8. 已忽略多余的。")
        if len(courses) == 0:
            self._logger.warn(f"没有待选课程")
            return True
        # 最多 9 个，格式如下。
        # tnos[i] 表示教师号，cids[i] 表示课程号。0 <= i <= 8
        data = {
            "tnos[0]": "",
            "cids[0]": ""
        }
        for i, c in enumerate(courses):
            courseSeq = c[0]
            teacherSeq = c[1]
            data["cids[%d]" % i] = courseSeq
            data["tnos[%d]" % i] = teacherSeq
        # 未使用的填充空字符
        for i in range(1 + i, 9):
            data["cids[%d]" % i] = ""
            data["tnos[%d]" % i] = ""

        r = self.http_post(
            "/CourseSelectionStudent/CourseSelectionSave", data=data)

        html = lxml.etree.HTML(r.text)
        table_rows = html.xpath("//table/tr/td/..")
        if len(table_rows) <= 1:
            # 无法自动分析结果
            import pathlib
            output_path = pathlib.Path("result.html").resolve()
            with output_path.open("w", encoding="utf-8") as file:
                file.write(r.text)
            self._logger.error(
                f"无法解析选课结果，原始结果已保存至{str(output_path)}。len(table_rows) = {len(table_rows)}")
            raise RuntimeError("无法解析选课结果")

        # 最后一行是 "关闭" 按钮
        del table_rows[-1]
        result = list()
        for tb_item in table_rows:
            tb_datas = tb_item.xpath("td/text()")
            tb_datas = [x.strip() for x in tb_datas]
            if len(tb_datas) == 6:
                item_result = SelectCourseResult(
                    courseSeq=tb_datas[1],
                    courseName=tb_datas[2],
                    teacherSeq=tb_datas[3],
                    teacherName=tb_datas[4],
                    failedCause=tb_datas[5],
                    success="成功" in tb_datas[5]
                )
                result.append(item_result)
            else:
                self._logger.error("选课结果解析失败：%s", "".join(tb_datas))
        return tuple(result)

    def waitting(self, interval, timeout=-1):
        """等待选课开始

        :interval: 刷新时间。
        :timeout: 最长等待时间，超出之后即使选课未开始也返回。-1 表示无穷大。
        """
        start = time.time()
        while not self.in_select_time():
            if timeout != -1 and (time.time() - start) > timeout:
                self._logger.info("等待超时")
                return
            self._logger.info("选课未开始")
            time.sleep(interval)
        self._logger.info("选课已经开始")
