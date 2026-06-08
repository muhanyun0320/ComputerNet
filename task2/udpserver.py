import socket
import struct
import random
import sys
import threading
import time

TYPE_CONN_REQ = 1
TYPE_CONN_ACK = 2
TYPE_DATA = 3
TYPE_ACK = 4
LOSS_RATE = 0.1
TOTAL_PACKETS = 50

ACK_DELAY = 0.05 #延迟ack时长

pending_ack = None #当前最新需要确认的数据包序号
ack_timer = None
timer_lock = threading.Lock()
client_addr = None
sock_global = None


def send_pending_ack():
    global pending_ack, ack_timer, sock_global, client_addr

    with timer_lock: #无待确认序号，清空定时器，直接退出
        if pending_ack is None:
            ack_timer = None
            return

        seq = pending_ack
        pending_ack = None
        ack_timer = None

    server_time = time.strftime("%H-%M-%S")
    sock_global.sendto(struct.pack(">HI", TYPE_ACK, seq) + server_time.encode(), client_addr)
    print(f"[ACK={seq + 1}]")


def schedule_ack(seq):
    global pending_ack, ack_timer

    with timer_lock:
        pending_ack = seq #更新待确认序号为最新收到的包序号

        if ack_timer is not None: #如果已有正在计时的定时器，取消旧定时器
            ack_timer.cancel()

        ack_timer = threading.Timer(ACK_DELAY, send_pending_ack)
        ack_timer.start() #重现开始计时

def immediate_ack(ack_num):
    server_time = time.strftime("%H-%M-%S")
    pkt = struct.pack(">HI", TYPE_ACK, ack_num)+server_time.encode()
    sock_global.sendto(pkt, client_addr)
    print(f"[重复帧即时ACK {ack_num+1}]")

#兜底：发送最后一批ack，与send_pending_ack()差不多
def cleanup_and_send():
    global pending_ack, ack_timer, sock_global, client_addr

    with timer_lock:
        if pending_ack is None:
            return

        seq = pending_ack
        pending_ack = None
        if ack_timer is not None:
            ack_timer.cancel()
            ack_timer = None

    server_time = time.strftime("%H-%M-%S")
    ack_pkt = struct.pack(">HI", TYPE_ACK, seq) + server_time.encode()
    sock_global.sendto(ack_pkt, client_addr)
    print(f"[ACK={seq + 1}]")

def handle_client(sock):
    global client_addr, pending_ack, ack_timer
    pending_ack = None
    ack_timer = None
    client_addr = None
    expect_seq = 0

    #判断
    while True:
        pkt, addr = sock.recvfrom(1024)
        if len(pkt) < 4:
            continue
        typ, sid = struct.unpack(">HH", pkt[:4])
        if typ != TYPE_CONN_REQ:
            continue
        dec = sid ^ 0x5A3C
        if not (0 <= dec <= 9999):
            print(f"[拒绝] 非法学号: {dec}")
            continue
        sock.sendto(struct.pack(">H", TYPE_CONN_ACK), addr)
        print(f"客户端 {addr} 连接成功 | 学号={dec}")
        client_addr = addr
        break

    while expect_seq < TOTAL_PACKETS:
        try:
            pkt, addr = sock.recvfrom(1024)
            if len(pkt) < 6:
                continue

            typ, seq = struct.unpack(">HI", pkt[:6])
            if typ != TYPE_DATA:
                continue

            if random.random() < LOSS_RATE:
                print(f"[丢包] 序号 {seq}")
                continue

            if seq > expect_seq:
                print(f"[丢弃乱序包] 收到{seq}，期望{expect_seq}")
                continue

            elif seq == expect_seq:
                expect_seq += 1
                schedule_ack(seq)

            else:
                print(f"[收到重复旧包{seq},期望{expect_seq},立即回复ACK]")
                immediate_ack(expect_seq - 1)

        except Exception as e:
            print(f"错误: {e}")

    time.sleep(ACK_DELAY + 0.02)
    cleanup_and_send()

    print(f"与客户端 {client_addr} 关闭连接")

def main():
    global sock_global
    if len(sys.argv) < 2:
        print("请输入: python udpserver.py <端口>")
        sys.exit(1)

    port = int(sys.argv[1])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock_global = sock
    print(f"服务端监听端口 {port}")

    while True:
        handle_client(sock)


if __name__ == "__main__":
    main()