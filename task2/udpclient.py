import socket
import struct
import time
import sys
import pandas as pd
import threading

STUDENT_ID = 2125 ^ 0x5A3C

TYPE_CONN_REQ = 1
TYPE_CONN_ACK = 2
TYPE_DATA = 3
TYPE_ACK = 4

LOG_FILE = "run_log.txt"

DATA_PACKET_SIZE = 80
WINDOW_SIZE = 5
TOTAL_PACKETS = 50

base = 0
next_seq = 0
rtt_samples = []
stats = []
lock = threading.Lock()
sock = None
server_addr = None
start_time_map = dict()
total_sent_packets = 0
SRTT = None
RTTVAR = None
ALPHA = 1/8
BETA = 1/4
retrans_flag = False #窗口是否重传
backoff_coeff = 1.0 #退避系数


def write_log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    ms = int((time.time() % 1) * 1000)
    t = f"{timestamp}.{ms:03d}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{t}] {msg}\n")

def calc_timeout(initial=0.3):
    global SRTT, RTTVAR
    with lock:
        if SRTT is None:
            return initial
        RTO_ms = SRTT + 4 * RTTVAR
        return max((RTO_ms / 1000)*backoff_coeff, 0.25)

def send_thread():
    global base, next_seq, total_sent_packets
    while True:
        with lock:
            if base >= TOTAL_PACKETS:
                break
            while next_seq < base + WINDOW_SIZE and next_seq < TOTAL_PACKETS:
                seq = next_seq
                start_byte = seq * DATA_PACKET_SIZE
                end_byte = (seq + 1) * DATA_PACKET_SIZE - 1

                data = b"DATA_%02d" % seq + b" " * (DATA_PACKET_SIZE - 7)
                pkt = struct.pack(">HI", TYPE_DATA, seq) + data
                sock.sendto(pkt, server_addr)
                start_time_map[seq] = time.time() #记录每个包的发送时间

                print(f"第{seq}个（第{start_byte}~{end_byte}字节）client端已经发送")
                write_log(f"第{seq}个（第{start_byte}~{end_byte}字节）client端已经发送")
                total_sent_packets += 1
                next_seq += 1


def ack_thread():
    global base, next_seq, retrans_flag, backoff_coeff
    while True:

        with lock:
            if base >= TOTAL_PACKETS:
                break

        sock.settimeout(calc_timeout())

        try:
            pkt, _ = sock.recvfrom(1024)
            ack_arrival_time = time.time() #收到ack报文的时间
            if len(pkt) < 6:
                continue

            ack_type, ack_seq = struct.unpack(">HI", pkt[:6])
            if ack_type != TYPE_ACK:
                continue

            server_time = pkt[6:].decode()


            with lock:
                if base <= ack_seq < base + WINDOW_SIZE:
                    for seq in range(base, ack_seq + 1):
                        if seq in start_time_map:
                            rtt = (ack_arrival_time - start_time_map.pop(seq)) * 1000

                            start_byte = seq * DATA_PACKET_SIZE
                            end_byte = (seq + 1) * DATA_PACKET_SIZE - 1

                            if not retrans_flag: #不是重发包
                                if seq==base: #只取窗口第一个包作为样本
                                    global SRTT, RTTVAR
                                    if SRTT is None:
                                        SRTT = rtt #加权RTT，旧值占7/8
                                        RTTVAR = rtt / 2 #抖动
                                    else:
                                        RTTVAR = (1 - BETA) * RTTVAR + BETA * abs(rtt - SRTT)
                                        SRTT = (1 - ALPHA) * SRTT + ALPHA * rtt

                                    rtt_samples.append(rtt)

                                stats.append({"seq": seq, "rtt": rtt}) #追加状态，用于pandas统计

                                print(f"第{seq}个（第{start_byte}~{end_byte}字节）server端已经收到，RTT={rtt:.2f} ms，server端系统时间={server_time}")
                                write_log(f"第{seq}个（第{start_byte}~{end_byte}字节）server端已经收到，RTT={rtt:.2f} ms，server端系统时间={server_time}")
                            else:
                                print(f"第{seq}个（第{start_byte}~{end_byte}字节）server端已经收到(重传后ACK，舍弃RTT采样)，server端系统时间={server_time}")
                                write_log(f"第{seq}个（第{start_byte}~{end_byte}字节）server端已经收到(重传后ACK，舍弃RTT采样)，server端系统时间={server_time}")

                    base = ack_seq+1
                    if retrans_flag:
                        retrans_flag = False
                        backoff_coeff = 1.0


        except socket.timeout:
            with lock:
                retrans_flag=True #超时重传窗口
                backoff_coeff *= 2
                re_start = base
                re_end = next_seq - 1
                for seq in range(re_start, re_end + 1):
                    s_b = seq * DATA_PACKET_SIZE
                    e_b = (seq + 1) * DATA_PACKET_SIZE - 1
                    print(f"即将重传第{seq}个（第{s_b}~{e_b}字节）数据包")
                    write_log(f"即将重传第{seq}个（第{s_b}~{e_b}字节）数据包")
                next_seq = base


def main():
    global sock, server_addr
    if len(sys.argv) < 3:
        print("请输入：python client.py <IP> <端口>")
        return

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    server_addr = (server_ip, server_port)

    #open(LOG_FILE, "w").close()
    write_log(f"客户端{server_ip}启动")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.3)

    conn_req = struct.pack(">H", TYPE_CONN_REQ) + struct.pack(">H", STUDENT_ID)
    sock.sendto(conn_req, server_addr)
    write_log("发送连接请求")

    try:
        pkt, client_addr = sock.recvfrom(1024)
        if struct.unpack(">H", pkt[:2])[0] == TYPE_CONN_ACK:
            print(f"客户端{client_addr}连接成功")
            write_log(f"客户端{client_addr}连接成功")
    except:
        print("连接超时")
        return

    t1 = threading.Thread(target=send_thread, daemon=True)
    t2 = threading.Thread(target=ack_thread, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    if stats:
        print("\n----------- 【汇总信息】 -----------")
        loss_rate = 1 - (TOTAL_PACKETS / total_sent_packets)
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