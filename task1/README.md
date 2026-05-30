## About ##

本项目基于 TCP 套接字+多线程 实现客户端与服务端通信。客户端对本地文件进行随机分块，按照自定义报文格式逐块发送数据；服务端采用多线程机制，独立处理每一个客户端连接，接收数据后完成字节反转并回传。客户端接收全部数据后，拼接生成反转后的新文件。服务端同步输出毫秒级运行日志，方便调试与抓包比对。


## Requirements ##

编程语言：Python 3.12
依赖说明：仅使用Python内置标准库，无需额外安装第三方包
内置模块：socket、struct、threading、random、sys、time


## Process ##

1.打开task1文件夹。
2.启动服务端：python reversetcpserver.py端口号 （如8888）。启动后服务端开始监听端口，自动生成run_log.txt日志文件。
3.准备测试文件：在项目目录下新建test.txt，作为待处理的原始文件。
4.启动多客户端：python client.py 服务端IP 端口号 目标文件 最小块大小 最大块大小 随机种子。运行完成后，目录下会生成 reversed_output.txt，即文件反转结果。

