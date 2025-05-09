import socket, threading, time
from core.config import BUFFER
from core.utils import get_all_local_ips

LOCAL_IPS       = get_all_local_ips()
DISCOVERY_PORT  = 9999
BROADCAST_INTERVAL = 5
PEER_TIMEOUT       = 60

_active_peers = {}    # ip -> (port, last_seen)
_lock         = threading.Lock()

def broadcast_hello(listen_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = f"Hello:{listen_port}".encode()
    while True:
        s.sendto(msg, ('255.255.255.255', DISCOVERY_PORT))
        time.sleep(BROADCAST_INTERVAL)

def listen_for_peers():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', DISCOVERY_PORT))
    while True:
        data, addr = s.recvfrom(BUFFER)
        ip = addr[0]
        if ip in LOCAL_IPS: continue
        if data.startswith(b'Hello:'):
            try:
                port = int(data.split(b':')[1])
                with _lock:
                    _active_peers[ip] = (port, time.time())
            except: pass

def get_active_peers(timeout=PEER_TIMEOUT):
    now = time.time()
    with _lock:
        return [(ip,port) for ip,(port,ts) in _active_peers.items() if now-ts<=timeout]

def start_discovery(listen_port):
    threading.Thread(target=broadcast_hello, args=(listen_port,), daemon=True).start()
    threading.Thread(target=listen_for_peers, daemon=True).start()
