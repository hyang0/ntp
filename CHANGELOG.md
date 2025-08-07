# 更新日志

所有项目的显著变更都将记录在此文件中。

格式基于[Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2023-11-01

### 新增
- 初始版本发布
- 通过UDP实现纯Python的NTP客户端
- 自动回退至备用NTP服务器列表
- 支持在Windows与Linux上同步系统时间
- 所有时间均以本地时区显示
- 命令行参数支持：--server, --set-system, --debug, --timeout, --threshold

### 修复
- 无（初始版本）

### 变更
- 无（初始版本）

### 移除
- 无（初始版本）