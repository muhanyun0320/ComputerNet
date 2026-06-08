## About ##

本项目基于 UDP 套接字和多线程实现 GBN 滑动窗口可靠数据传输。
由于 UDP 本身是无连接、不可靠传输协议，本程序在 UDP 基础上自主实现一套可靠传输机制：包含简易身份握手、滑动窗口流水线发送、累积确认、延迟 ACK、随机网络丢包模拟、基于 Jacobson 算法的动态 RTT/RTO 超时计算、超时重传、超时指数退避、Karn 算法等核心功能。
客户端与服务端采用自定义二进制报文格式通信，双线程分别处理数据发送与 ACK 接收；程序全程生成毫秒级运行日志，传输结束后自动统计丢包率、RTT 均值 / 最值 / 标准差等网络指标，便于实验分析与问题排查。


## Requirements ##

编程语言：Python 3.12
依赖说明：仅使用Python内置标准库，无需额外安装第三方包
内置模块：socket、struct、threading、random、sys、time、pandas、random


## Process ##

1.打开task2文件夹。
2.启动服务端：python udpserver.py 端口号 （如8888）。启动后服务端开始监听端口。
3.启动客户端：python udpclient.py 服务端IP 端口号（如127.0.0.1 8888）。
4.生成run_log.txt日志文件。


