import struct
import socket
import sys
import random
import threading  # 加了这个

TYPE_INIT = 1
TYPE_AGREE = 2
TYPE_REV_REQ = 3
TYPE_REV_ANS = 4

#文件分块
def split_file(file_path, lmin, lmax, seed):
    random.seed(seed)
    with open(file_path, "rb") as f:
        content = f.read()
    chunks = []
    offset = 0 #当前位置指针，标记读到哪了
    total = len(content)
    while offset < total:
        if total - offset <= lmax:
            cl = total - offset
        else:
            cl = random.randint(lmin, lmax) #随机生成块大小
        chunks.append(content[offset:offset+cl])
        offset += cl
    return chunks, len(chunks)

def client_main():
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    file_path = sys.argv[3] #test.txt
    lmin = int(sys.argv[4]) #最小快
    lmax = int(sys.argv[5]) #最大快
    seed = int(sys.argv[6]) #随机种子

    chunks, N = split_file(file_path, lmin, lmax, seed)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port)) #连接服务端

    sock.sendall(struct.pack(">HI", TYPE_INIT, N)) #发送init报文

    sock.recv(2) #接受Agreed报文

    result = []
    for i, c in enumerate(chunks, 1):
        sock.sendall(struct.pack(">HI", TYPE_REV_REQ, len(c)) + c) #发送请求报文

        h = sock.recv(6) #接受应答报文的头部
        _, len = struct.unpack(">HI", h) #解包头部以获得length
        data = sock.recv(len) #接受应答报文rev_data
        result.append(data)
        print(f"第{i}块结果: {data.decode()}")

    with open("reversed_output.txt", "wb") as f:
        f.write(b"".join(result)) #拼接每块result，写入输出文件
    print("完成！结果保存在 reversed_output.txt")
    sock.close()

if __name__ == "__main__":
    client_main()
