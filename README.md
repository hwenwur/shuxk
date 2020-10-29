# 上海大学选（qiang）课程序

2020/10/29:
**由于选课系统升级，本项目暂时不可用。**

## 使用方法
将待选课程添加到 courses.txt, 然后运行
```shell
python run.py 学号
```

## 自定义刷新时间

可自行修改 `shuxk/__main__.py` 文件

## 杂项

清理临时文件
```shell
make clean
```

打包项目
```shell
make pack
```

统计代码行数
```shell
make cloc
```
