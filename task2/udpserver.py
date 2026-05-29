import socket
import struct
import random
import sys

TYPE_CONN_REQ = 1
TYPE_CONN_ACK = 2
TYPE_DATA = 3
TYPE_ACK = 4
LOSS_RATE = 0.2 #20%随机丢包概率
TOTAL_PACKETS=30 #需要传的总包树


def main():
    port = int(sys.argv[1])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port)) #监听本机所有网卡的指定端口
    print(f"服务端监听端口 {port}")

    client_addr = None
    expect_seq = 0

    while True:
        pkt, addr = sock.recvfrom(1024)
        if len(pkt) < 2:
            continue
        typ = struct.unpack(">H", pkt[:2])[0]

        if typ == TYPE_CONN_REQ:
            if len(pkt) < 4:
                continue
            _, sid = struct.unpack(">HH", pkt[:4])
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
            #if addr != client_addr:
            #    continue
            if len(pkt) < 6:
                continue

            typ, seq = struct.unpack(">HI", pkt[:6])
            if typ != TYPE_DATA:
                continue

            if random.random() < LOSS_RATE: #模拟丢包
                print(f"[丢包] 序号 {seq}")
                continue

            if seq == expect_seq: #只收接受窗口中的目标包
                sock.sendto(struct.pack(">HI", TYPE_ACK, seq), addr)
                start_byte = seq * 80
                end_byte = (seq + 1) * 80 - 1
                print(f"[ACK] 第{seq}个（第{start_byte}~{end_byte}字节）server端已经收到")
                expect_seq += 1
            else:
                print(f"[丢弃乱序包] 收到{seq}，期望{expect_seq}")

        except Exception as e:
            print(f"错误: {e}")
    print(f"与客户端 {addr} 关闭连接")


if __name__ == "__main__":
    main()