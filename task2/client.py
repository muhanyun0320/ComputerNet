import socket
import struct
import time
import sys
import pandas as pd
import threading

# 学号后四位 2125
STUDENT_ID = 2125 ^ 0x5A3C

TYPE_CONN_REQ = 1 #请求连接
TYPE_CONN_ACK = 2 #应答链接
TYPE_DATA = 3 #数据报文
TYPE_ACK = 4 #ACK确认报文

LOG_FILE = "run_log.txt"

DATA_PACKET_SIZE = 80 #每个数据报数据部分80B，加上头部6B
WINDOW_SIZE = 5 #发送窗口大小
TOTAL_PACKETS = 30 #设定总共发30个波

base = 0 #最早未确认的包，窗口左沿
next_seq = 0 #下一个要发送的序号
rtt_samples = [] #存每次ACK的RTT，用于设定超时时长
stats = [] #记录每个ACK对应的序号+RTT，后续用pandas做统计
lock = threading.Lock() #避免send和ack线程对共享变量的同时修改
sock = None
server_addr = None
start_time_map = dict() #记录发包时间
total_sent_packets = 0  #记录实际发送的总次数，用于计算丢包率

def write_log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    ms = int((time.time() % 1) * 1000) #精确到ms便于与wireshark时间比对
    t = f"{timestamp}.{ms:03d}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{t}] {msg}\n")

def calc_timeout(multiplier=4, initial=0.3):
    with lock:
        if not rtt_samples: #无RTT样本时先设为300ms
            return initial
        avg = sum(rtt_samples) / len(rtt_samples)
        return max(avg * multiplier / 1000, 0.1) #避免过于小，易诱发超时

#发报文
def send_thread():
    global base, next_seq, total_sent_packets
    while True:
        with lock:
            if base >= TOTAL_PACKETS: #当前发送窗口所有包都已发完
                break
            while next_seq < base + WINDOW_SIZE and next_seq < TOTAL_PACKETS: #窗口未满，且没发够30个
                seq = next_seq

                start_byte = seq * DATA_PACKET_SIZE
                end_byte = (seq + 1) * DATA_PACKET_SIZE - 1

                data = b"DATA_%02d" % seq + b" " * (DATA_PACKET_SIZE - 7) #构造80B的报文数据
                pkt = struct.pack(">HI", TYPE_DATA, seq) + data #构造数据报文，加上6B头部共86B
                sock.sendto(pkt, server_addr)
                start_time_map[seq] = time.time() #记录当前发送时间
                print(f"第{seq}个（第{start_byte}~{end_byte}字节）client端已经发送")
                write_log(f"第{seq}个（第{start_byte}~{end_byte}字节）client端已经发送")
                total_sent_packets += 1
                next_seq += 1

#收ACK
def ack_thread():
    global base, next_seq
    while True:
        with lock:
            if base >= TOTAL_PACKETS:
                break

        sock.settimeout(calc_timeout())  # 更新超时时间

        try:
            pkt, _ = sock.recvfrom(1024)
            ack_type, ack_seq = struct.unpack(">HI", pkt[:6]) #获取报文头部
            if ack_type != TYPE_ACK:
                continue

            with lock:
                if base <= ack_seq < base + WINDOW_SIZE:
                    rtt = (time.time() - start_time_map.pop(ack_seq)) * 1000
                    rtt_samples.append(rtt)
                    stats.append({"seq": ack_seq, "rtt": rtt})

                    start_byte = ack_seq * DATA_PACKET_SIZE
                    end_byte = (ack_seq + 1) * DATA_PACKET_SIZE - 1
                    print(f"第{ack_seq}个（第{start_byte}~{end_byte}字节）server端已经收到，RTT={rtt:.2f} ms")
                    write_log(f"第{ack_seq}个（第{start_byte}~{end_byte}字节）server端已经收到，RTT={rtt:.2f} ms")

                    base = ack_seq + 1

        except socket.timeout:
            with lock:
                re_start = base
                re_end = next_seq - 1
                for seq in range(re_start, re_end + 1):
                    s_b = seq * DATA_PACKET_SIZE
                    e_b = (seq + 1) * DATA_PACKET_SIZE - 1
                    print(f"重传第{seq}个（第{s_b}~{e_b}字节）数据包")
                    write_log(f"重传第{seq}个（第{s_b}~{e_b}字节）数据包")
                next_seq = base #全部重传

def main():
    global sock, server_addr
    if len(sys.argv) < 3:
        print("请输入：python client.py <IP> <端口>")
        return

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    server_addr = (server_ip, server_port)

    open(LOG_FILE, "w").close() #清空日志
    write_log("客户端启动")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #IPv4，UDP
    sock.settimeout(0.3)

    conn_req = struct.pack(">H", TYPE_CONN_REQ) + struct.pack(">H", STUDENT_ID) #发送连接请求报文，携带报文类型和学号
    sock.sendto(conn_req, server_addr)
    write_log("发送连接请求")

    try:
        pkt, client_addr = sock.recvfrom(1024)
        if struct.unpack(">H", pkt[:2])[0] == TYPE_CONN_ACK: #返回的是元组要用【0】访问
            print(f"客户端{client_addr}连接成功")
            write_log(f"客户端{client_addr}连接成功")
    except:
        print("连接超时")
        return

    t1 = threading.Thread(target=send_thread, daemon=True)
    t2 = threading.Thread(target=ack_thread, daemon=True)
    t1.start()
    t2.start()
    t1.join() #主线程阻塞，等待两个子线程全部执行完毕
    t2.join()

    #计算指标
    if stats:
        print("\n====== 【汇总信息】 ======")
        loss_rate = 1 - (TOTAL_PACKETS / total_sent_packets) #丢包率
        print(f"丢包率: {loss_rate*100:.2f}%")

        df = pd.DataFrame(stats)
        print(f"平均RTT: {df['rtt'].mean():.2f} ms")
        print(f"最大RTT: {df['rtt'].max():.2f} ms")
        print(f"最小RTT: {df['rtt'].min():.2f} ms")
        print(f"RTT标准差: {df['rtt'].std():.2f} ms")

        write_log(f"汇总：丢包率={loss_rate*100:.2f}%, 平均RTT={df['rtt'].mean():.2f}, 最大={df['rtt'].max():.2f}, 最小={df['rtt'].min():.2f}, 标准差={df['rtt'].std():.2f}")

    sock.close()

if __name__ == "__main__":
    main()