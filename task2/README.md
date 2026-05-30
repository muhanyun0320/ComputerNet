## About ##

本项目基于UDP+GBN协议实现可靠数据传输。客户端采用滑动窗口机制并发发送数据报文，双线程分别负责发包与接收ACK；服务端模拟20%随机丢包，遵循GBN规则仅接收有序报文，乱序包直接丢弃。客户端支持动态计算超时时间、统计丢包率与RTT相关指标，全程生成毫秒级日志，可配合抓包工具调试比对，同时内置学号异或校验完成身份认证。


## Requirements ##

编程语言：Python 3.12
依赖说明：内置模块 + 第三方库 pandas
所需依赖：socket、struct、threading、random、sys、time、pandas


## Process ##

1.打开 task2 文件夹.
2.安装依赖：pip install pandas.
3.启动服务端：python server.py端口号（如 8888），启动后监听端口并等待客户端连接。
4.启动客户端：python client.py服务端IP端口号，本地测试P填写127.0.0.1。运行完成后，目录自动生成run_log.txt日志文件，控制台输出丢包率、平均/最大/最小RTT及标准差。


