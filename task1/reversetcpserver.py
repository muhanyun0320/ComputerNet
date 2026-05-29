import socket
import threading #多线程
import struct #打包/解包报文
import time #获得时间戳
import sys #获取命令行参数

LOG_FILE = "run_log.txt" #日志文件
#四种报文类型
TYPE_INIT = 1
TYPE_AGREE = 2
TYPE_REV_REQ = 3
TYPE_REV_ANS = 4

#日志锁，防止多线程写冲突
log_lock = threading.Lock()

#写日志
def write_log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    ms = int((time.time() % 1) * 1000) #精确到ms便于与wireshark时间比对
    t = f"{timestamp}.{ms:03d}"
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{t}] {msg}\n")

def handle_client(conn, addr): #addr = (IP, 端口)
    print(f"\n[服务端] 新客户端连接：{addr}")
    write_log(f"客户端 {addr} 已连接")

    try:
        #接收初始化报文
        init_pkt = conn.recv(6)
        type_, N = struct.unpack(">HI", init_pkt) #解包：>HI(>大端序；H无符号短整型2B，对应报文类型；I无符号整型4B，对应块数量
        if type_ != TYPE_INIT:
            return
        print(f"[服务端] 客户端 {addr} 发送初始化，块数N={N}")
        write_log(f"收到Initialization，N={N}")

        #回复Agree报文
        conn.sendall(struct.pack(">H", TYPE_AGREE))
        print(f"[服务端] 向客户端 {addr} 发送Agree报文")
        write_log("发送Agree报文")

        #循环处理每个数据块
        for i in range(1, N+1):
            #接收请求报文
            header = conn.recv(6) #先接受报文头部
            type_, length = struct.unpack(">HI", header)
            if type_ != TYPE_REV_REQ:
                break
            req_data = conn.recv(length)
            print(f"[服务端] 客户端 {addr} 第{i}块，长度={length}")
            write_log(f"收到第{i}块，长度={length}")

            #强制延时0.5秒，让客户端变慢，保证能看到“同时处理”
            time.sleep(0.5)

            #反转数据
            rev_data = req_data[::-1]

            # 发送应答报文
            ans_pkt = struct.pack(">HI", TYPE_REV_ANS, len(rev_data)) + rev_data
            conn.sendall(ans_pkt)
            print(f"[服务端] 向客户端 {addr} 发送第{i}块反转结果")
            write_log(f"返回第{i}块反转结果")

        print(f"[服务端] 客户端 {addr} 所有块处理完成")

    except Exception as e:
        print(f"[服务端] 客户端 {addr} 异常断开: {e}")
        write_log(f"客户端 {addr} 异常: {e}")
    finally:
        conn.close()
        print(f"[服务端] 客户端 {addr} 已断开连接\n")
        write_log(f"客户端 {addr} 断开")

def main():
    if len(sys.argv) < 2:
        print("用法：python reversetcpserver.py <端口号>")
        print("使用默认端口 8888")
        port = 8888
    else:
        port = int(sys.argv[1])

    #清空日志文件
    open(LOG_FILE, "w").close()

    # 创建TCP套接字
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #IPv4,TCP
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #端口复用，防止短时内重启报错
    server.bind(("0.0.0.0", port))
    server.listen(5)  #允许最多5个客户端排队等待，而并非最多5个客户端多线程发报文

    print("=" * 50)
    print(f"多线程TCP服务端已启动，监听端口 {port}")
    write_log(f"服务端启动，监听端口 {port}")

    while True:
        #主线程只负责接收新连接
        conn, addr = server.accept() #等待连接
        # 每个客户端创建一个独立线程处理
        client_thread = threading.Thread(target=handle_client, args=(conn, addr)) #target：该线程要跑的函数；args：传给target函数的参数
        client_thread.daemon = True  #主线程退出时子线程自动结束
        client_thread.start() #启动该线程

if __name__ == "__main__":
    main()