# -*- coding: utf-8 -*-
from .models import SHUer
from .courseapi import CourseAPI, CannotJudgeError
import logging
import pathlib
import time
import sys
from getpass import getpass


# 选课开始之前刷新间隔
BEFORE_INTERNAL = 30
# 选课状态未知(获取失败)刷新间隔
FAILED_INTERNAL = 5
# 选课开始后刷新间隔
SELECT_INTERNAL = 3

help_content = """使用说明：python run.py 学号
安装依赖：pip install -r requirements.txt
请在本文件所在文件夹执行上述命令。
必须解压后再运行， 添加课程可编辑 courses.txt 文件
"""
logger = logging.getLogger(__name__)


def setup_logger():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    hd = logging.StreamHandler()
    hd.setFormatter(logging.Formatter("%(asctime)s-%(name)s-%(levelname)s:%(message)s"))
    root.addHandler(hd)

    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


def read_courses():
    result = []
    with open("courses.txt", encoding="utf-8") as file:
        for line in file:
            if line.startswith("#"):
                continue
            if not line:
                continue
            courseSeq, teacherSeq = line.split("-")
            result.append((courseSeq.strip(), teacherSeq.strip()))
    logger.debug(f"待选课程:{result}")
    return result


def main():
    if len(sys.argv) != 2 or len(sys.argv[1]) != 8:
        print(help_content)
        return
    setup_logger()
    try:
        studentCode = int(sys.argv[1])
    except ValueError:
        print("学号格式错误")
        return
    cache_file = ".user%d" % studentCode
    if pathlib.Path(cache_file).exists():
        user = SHUer.from_file(cache_file)
    else:
        password = getpass()
        user = SHUer(studentCode, password)

    try:
        user.refershToken()
        user.dump_to(cache_file)
        print("登录成功!")
    except RuntimeError as e:
        print(f"登录失败:{e.args}")
        return

    api = CourseAPI(user)

    info = api.get_course_info("00853619", "1774")
    print(info)
    # courses = read_courses()
    # for x in courses:
    #     print(f"待选课程：{x[0]}-{x[1]}")

    # while True:
    #     try:
    #         select_time = api.is_select_time()
    #         if select_time:
    #             print("开始选课...")
    #             break
    #         else:
    #             print("选课未开始")
    #             time.sleep(BEFORE_INTERNAL)
    #     except CannotJudgeError:
    #         print("无法判断")
    #         time.sleep(FAILED_INTERNAL)
    # while not (r := api.select_course(courses)):
    #     print(f"选课失败，{SELECT_INTERNAL}秒后重试...")
    #     time.sleep(SELECT_INTERNAL)
    # print("选课结果:")
    # for x in r:
    #     print(x)


if __name__ == "__main__":
    main()
