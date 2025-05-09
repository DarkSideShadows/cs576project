import socket, subprocess, re
from core.config import BUFFER

def send_msg(sock, msg):
    sock.sendall(msg.encode())

def recv_msg(sock):
    try: return sock.recv(BUFFER).decode()
    except: return ""

def get_all_local_ips():
    ips = set()
    # method 1
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1",1))
        ips.add(s.getsockname()[0]); s.close()
    except: pass
    # method 2
    try:
        hn = socket.gethostname()
        for info in socket.getaddrinfo(hn, None, socket.AF_INET):
            ips.add(info[4][0])
    except: pass
    # method 3
    try:
        out = subprocess.check_output(["ip","-4","addr"], encoding="utf-8")
        for ip in re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", out):
            if not ip.startswith("127."): ips.add(ip)
    except: pass
    ips.add("127.0.0.1")
    return ips
