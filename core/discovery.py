# Peer Discovery via UDP broadcast

import socket
import threading
import time

from core.config import BUFFER
from core.utils import get_all_local_ips
LOCAL_IPS = get_all_local_ips()

DISCOVERY_PORT = 9999   # port for UDP broadcast/listening
BROADCAST_INTERVAL = 5  # seconds between sending hello packets
PEER_TIMEOUT = 60       # time before a peer is considered inactive

active_peers = {}       # {ip: last_seen_timestamp}
lock = threading.Lock() # thread-safe access to active_peers


# periodically broadcasts a hello message containing this peer's listening port
def broadcast_hello(listen_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    msg = f"Hello:{listen_port}".encode()
    interval = BROADCAST_INTERVAL
    stable_peers = 0

    while True:
        s.sendto(msg, ('255.255.255.255', DISCOVERY_PORT))
        time.sleep(interval)

        # adjust interval based on peer count changes
        current_peers = len(get_active_peers())
        if current_peers == stable_peers:
            interval = min(interval + 1, 30) # gradual backoff
        else:
            interval = BROADCAST_INTERVAL # reset if peers changed
            stable_peers = current_peers
    
# listens for hello messages from other peers and updates the active_peers dictionary with timestamps
def listen_for_peers():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', DISCOVERY_PORT))

    while True:
        data, addr = s.recvfrom(BUFFER)
        ip = addr[0]

        if ip in LOCAL_IPS:
            continue # skip yourself

        try:
            if data.startswith(b'Hello:'):
                port = int(data.split(b':')[1])
                with lock:
                    active_peers[ip] = (port, time.time())
        except Exception as e:
            print(f"[Discovery] Error parsing packet from {ip}: {e}")

# returns a list of (ip, port) tuples for peers active within the timeout
def get_active_peers(timeout=PEER_TIMEOUT):
    now = time.time()
    with lock:
        return [(ip, port) for ip, (port, last_seen) in active_peers.items() if now - last_seen <= timeout]
    
# starts broadcasting and listening in background threads
def start_discovery(listen_port):
    threading.Thread(target=broadcast_hello, args=(listen_port,), daemon=True).start()
    threading.Thread(target=listen_for_peers, daemon=True).start()