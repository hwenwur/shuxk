# 上海大学抢课程序

2020/10/29:
**由于选课系统更新，本程序还未经过充分测试。可用性未知。**

## 基本思路
本项目适用于二轮、三轮选课，系统限制容量的情况。**对一轮选课按绩点排序的模式无效**。

- 普通模式：在选课开始前，定时刷新选课系统界面，判断是否已经到选课时间，如果已到选课时间，立即开始选课。
- 捡漏模式：在选课期间，定时刷新某门课程容量，如果有空余（扩容或有人退课）立即选课。

## 安装依赖
```shell
pip install -r requirements.txt
```
如果下载速度很慢，可以尝试使用国内镜像，例如：[tuna](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)。

## 使用方法
将待选课程添加到 courses.txt, 然后运行
```shell
python run.py 学号
```

## 自定义刷新时间

可自行修改 `shuxk/__main__.py` 文件
