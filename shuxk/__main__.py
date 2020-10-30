# -*- coding: utf-8 -*-
import logging
import os
import pathlib
import sys
import time
from getpass import getpass

from .courseapi import CannotJudgeError, CourseAPI
from .models import SHUer

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
    """初始化日志
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    hd = logging.StreamHandler()
    hd.setFormatter(logging.Formatter(
        "%(asctime)s-%(name)s-%(levelname)s:%(message)s"))
    root.addHandler(hd)

    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


def read_courses():
    """
    :return: 返回数据格式[(课程号，教师号), ...]
    """
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
    setup_logger()

    if len(sys.argv) != 2 or len(sys.argv[1]) != 8:
        print(help_content)
        return

    studentCode = sys.argv[1]
    if len(studentCode) != 8:
        print("学号格式错误")
        return

    password = getpass("登录密码：")
    user = SHUer(studentCode, password)

    user.refershToken()

    api = CourseAPI(user.studentCode, user.token)
    courses = read_courses()
    for x in courses:
        print(f"待选课程：{x[0]}-{x[1]}")

    while True:
        try:
            api.waitting(BEFORE_INTERNAL)
            break
        except CannotJudgeError:
            time.sleep(FAILED_INTERNAL)
        except KeyboardInterrupt:
            print("程序终止")
            sys.exit(1)

    while not (r := api.select_course(courses)):
        print(f"选课失败，{SELECT_INTERNAL}秒后重试...")
        time.sleep(SELECT_INTERNAL)

    print("选课结果:")
    for x in r:
        print(x)


if __name__ == "__main__":
    main()
