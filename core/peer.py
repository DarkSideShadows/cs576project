# core/peer.py
import asyncio, threading, socket, os, time
from datetime import datetime
from core.config    import DEFAULT_PORT, BUFFER
from core.discovery import start_discovery, get_active_peers
from core.utils     import get_all_local_ips
from core.commands  import handle_command, RestartChatException, ExitProgramException
from crypto.crypto_utils import (
    generate_key_pair, serialize_public_key,
    deserialize_public_key, encrypt_message,
    decrypt_message
)
from bridge         import broadcast_to_browsers   # your aiohttp bridge

# ——— UI hook (injected by main.py) —————————————————————————————
_ui_broadcaster = lambda line: None
def set_ui_broadcaster(fn):
    global _ui_broadcaster
    _ui_broadcaster = fn

def ui_broadcast(line: str):
    _ui_broadcaster(line)

# ——— Global state —————————————————————————————————————————————
connections      = []     # list of (socket, peer_id)
peer_public_keys = {}     # peer_id -> public key
peer_names       = {}     # peer_id -> nickname
LOCAL_IPS        = get_all_local_ips()
my_private_key, my_public_key = generate_key_pair()

# ——— Networking machinery ——————————————————————————————————————
def start_connection_listener(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', port))
    s.listen()
    def accept_loop():
        while True:
            conn, addr = s.accept()
            perform_handshake(conn, addr[0], addr[1], incoming=True)
    threading.Thread(target=accept_loop, daemon=True).start()

def initiate_peer_connections(host, port):
    pid = f"{host}:{port}"
    if pid in peer_names:
        return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        perform_handshake(s, host, port, incoming=False)
    except Exception as e:
        ui_broadcast(f"[!] Connection to {host}:{port} failed: {e}")

def perform_handshake(sock, host, port, incoming):
    pid = f"{host}:{port}"
    try:
        # 1) key exchange
        if incoming:
            peer_bytes = sock.recv(BUFFER)
            peer_public_keys[pid] = deserialize_public_key(peer_bytes)
            sock.sendall(serialize_public_key(my_public_key))
        else:
            sock.sendall(serialize_public_key(my_public_key))
            peer_bytes = sock.recv(BUFFER)
            peer_public_keys[pid] = deserialize_public_key(peer_bytes)

        # 2) name exchange
        if incoming:
            their_name = sock.recv(BUFFER).decode().strip()
            sock.sendall(my_name.encode())
        else:
            sock.sendall(my_name.encode())
            their_name = sock.recv(BUFFER).decode().strip()

        peer_names[pid] = their_name or pid
        connections.append((sock, pid))
        ui_broadcast(f"[+] Secure connection established with {peer_names[pid]} ({pid})")

        # 3) spawn listener
        threading.Thread(
            target=listen_for_messages,
            args=(sock, pid),
            daemon=True
        ).start()

    except Exception as e:
        sock.close()
        ui_broadcast(f"[!] Handshake failed for {pid}: {e}")

def listen_for_messages(sock, pid):
    while True:
        try:
            data = sock.recv(BUFFER)
        except:
            break
        if not data:
            break
        try:
            msg = decrypt_message(my_private_key, data)
            ts  = datetime.now().strftime("%H:%M")
            ui_broadcast(f"[{ts}] {peer_names.get(pid,pid)}: {msg}")
        except:
            pass
    sock.close()

def send_user_message(msg: str):
    ts   = datetime.now().strftime("%H:%M")
    ui_broadcast(f"[{ts}] You: {msg}")
    for sock, pid in list(connections):
        if pid in peer_public_keys:
            try:
                cipher = encrypt_message(peer_public_keys[pid], msg)
                sock.sendall(cipher)
            except:
                pass

# ——— Browser input handler ——————————————————————————————————————
async def handle_browser_input(queue: asyncio.Queue):
    while True:
        msg = await queue.get()
        if not msg:
            continue
        if msg.startswith('/'):
            try:
                handle_command(
                    cmd=msg,
                    my_name=my_name,
                    connections=connections,
                    peer_names=peer_names,
                    peer_public_keys=peer_public_keys,
                    ui_broadcast=ui_broadcast
                )
            except (RestartChatException, ExitProgramException):
                return
        else:
            send_user_message(msg)

# ——— Main “in-browser” chat startup ———————————————————————————
async def start_chat_node(browser_queue: asyncio.Queue):
    global my_name

    # 1) nickname
    ui_broadcast("Enter your nickname:")
    my_name = (await browser_queue.get()).strip() or "Anonymous"
    ui_broadcast(f"✔︎ Hello, {my_name}!")

    # 2) port
    ui_broadcast(f"Enter your listening port (default {DEFAULT_PORT}):")
    raw = (await browser_queue.get()).strip()
    port = int(raw) if raw.isdigit() else DEFAULT_PORT
    ui_broadcast(f"[*] Will listen on port {port}")

    start_connection_listener(port)
    start_discovery(port)

    # 3) LAN vs ngrok vs quit
    ui_broadcast("Choose connection mode:\n1) LAN discovery\n2) ngrok tunnel\n3) Quit")
    choice = (await browser_queue.get()).strip()
    if choice == "3":
        raise ExitProgramException()

    if choice == "2":
        ui_broadcast("Enter ngrok auth token (or Enter to skip):")
        token = (await browser_queue.get()).strip()
        print("[debug] Got input from browser")
        if token:
            from pyngrok import ngrok
            try:
                ngrok.set_auth_token(token)
                tunnel = ngrok.connect(port, "tcp")
                ui_broadcast(f"[*] ngrok public tunnel at {tunnel.public_url}")
            except Exception as e:
                ui_broadcast(f"[!] ngrok failed: {e}")
    else:
        ui_broadcast(f"[*] LAN discovery enabled")

    # ready
    ui_broadcast("[*] Ready – type /help or your message")
    await chat_loop(browser_queue, my_name)

async def chat_loop(browser_queue: asyncio.Queue, my_name: str):
    # spawn browser reader
    asyncio.create_task(handle_browser_input(browser_queue))
    # keep alive
    while True:
        await asyncio.sleep(3600)