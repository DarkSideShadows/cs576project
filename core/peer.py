# core/peer.py
import socket
import threading
import time
import asyncio
import os
from datetime import datetime

from core.discovery import start_discovery, get_active_peers
from core.utils     import get_all_local_ips
from core.config    import DEFAULT_PORT, BUFFER
from core.commands  import handle_command, RestartChatException, ExitProgramException
from crypto.crypto_utils import (
    generate_key_pair,
    serialize_public_key,
    deserialize_public_key,
    encrypt_message,
    decrypt_message
)
from bridge import broadcast_to_browsers

# ─── Global State ───────────────────────────────────────────────────────────
connections      = []      # list of (socket, peer_id)
conn_peer_map    = {}      # socket → peer_id
peer_public_keys = {}      # peer_id → RSA public key
connected_ids    = set()   # set of peer_id
peer_names       = {}      # peer_id → nickname
my_name          = ""      
LOCAL_IPS        = get_all_local_ips()
my_private_key, my_public_key = generate_key_pair()

# ─── Connection Listener & Handshake ────────────────────────────────────────
def start_connection_listener(port):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('', port))
    listener.listen()
    print(f"[*] Listening on port {port}")
    def _accept_loop():
        while True:
            try:
                conn, addr = listener.accept()
                perform_handshake(conn, addr, is_incoming=True)
            except Exception as e:
                print(f"[!] Listener error: {e}")
                break
    threading.Thread(target=_accept_loop, daemon=True).start()

def perform_handshake(sock, addr, is_incoming):
    peer_id = sock.getpeername()[0] if is_incoming else addr[0]
    try:
        # 1) Exchange public keys
        if is_incoming:
            other_pk = sock.recv(BUFFER)
            peer_public_keys[peer_id] = deserialize_public_key(other_pk)
            sock.sendall(serialize_public_key(my_public_key))
        else:
            sock.sendall(serialize_public_key(my_public_key))
            other_pk = sock.recv(BUFFER)
            peer_public_keys[peer_id] = deserialize_public_key(other_pk)

        # 2) Exchange nicknames
        if is_incoming:
            their_name = sock.recv(BUFFER).decode().strip()
            sock.sendall(my_name.encode())
        else:
            sock.sendall(my_name.encode())
            their_name = sock.recv(BUFFER).decode().strip()

        # 3) Record connection
        peer_names[peer_id] = their_name or peer_id
        connections.append((sock, peer_id))
        conn_peer_map[sock] = peer_id
        connected_ids.add(peer_id)

        banner = f"[+] Secure connection with {peer_names[peer_id]} ({peer_id})"
        print(banner)
        broadcast_to_browsers(banner)

        # 4) Start listening for encrypted messages
        threading.Thread(
            target=listen_for_messages,
            args=(sock, peer_id),
            daemon=True
        ).start()

    except Exception as e:
        print(f"[!] Handshake failed for {peer_id}: {e}")
        sock.close()

def initiate_peer_connections(host, port):
    if host in connected_ids:
        return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        perform_handshake(s, (host, port), is_incoming=False)
    except Exception as e:
        print(f"[!] Connection to {host}:{port} failed: {e}")

# ─── Message I/O ─────────────────────────────────────────────────────────────
def listen_for_messages(sock, peer_id):
    while True:
        try:
            data = sock.recv(BUFFER)
        except:
            break
        if not data:
            break
        try:
            msg = decrypt_message(my_private_key, data)
            ts  = datetime.now().strftime('%H:%M')
            line = f"[{ts}] {peer_names.get(peer_id, peer_id)}: {msg}"
            print(line)
            broadcast_to_browsers(line)
        except:
            continue

    # cleanup on disconnect
    name = peer_names.pop(peer_id, peer_id)
    out  = f"[*] {name} disconnected"
    print(out)
    broadcast_to_browsers(out)
    try: sock.close()
    except: pass
    connections[:] = [(s,p) for s,p in connections if p != peer_id]
    peer_public_keys.pop(peer_id, None)
    connected_ids.discard(peer_id)
    conn_peer_map.pop(sock, None)

def prompt_and_send_messages():
    while True:
        msg = input().strip()
        if not msg:
            continue

        # commands (`/quit`, `/exit`, etc.) raise exceptions
        if msg.startswith('/'):
            handle_command(msg, my_name, connections, peer_names, peer_public_keys)
            continue

        # normal chat message
        ts   = datetime.now().strftime('%H:%M')
        line = f"[{ts}] You: {msg}"
        print(line)
        broadcast_to_browsers(line)
        for sock, pid in list(connections):
            if pid not in peer_public_keys:
                continue
            try:
                enc = encrypt_message(peer_public_keys[pid], msg)
                sock.sendall(enc)
            except:
                pass

# ─── Browser→P2P Bridge ──────────────────────────────────────────────────────
async def forward_browser_messages(queue: asyncio.Queue):
    while True:
        msg = await queue.get()
        if not msg:
            continue
        msg = msg.strip()
        if msg.startswith('/'):
            handle_command(msg, my_name, connections, peer_names, peer_public_keys)
        else:
            ts   = datetime.now().strftime('%H:%M')
            line = f"[{ts}] You: {msg}"
            print(line)
            broadcast_to_browsers(line)
            for sock, pid in list(connections):
                if pid in peer_public_keys:
                    try:
                        enc = encrypt_message(peer_public_keys[pid], msg)
                        sock.sendall(enc)
                    except:
                        pass

# ─── Main Entry Point ────────────────────────────────────────────────────────
async def start_chat_node(browser_queue=None):
    global my_name

    # 1) Nickname (force non‐empty)
    while True:
        my_name = input("Enter your nickname: ").strip()
        if my_name:
            break
        print("[!] Nickname cannot be empty.")

    # 2) Wire up browser relay
    if browser_queue:
        asyncio.create_task(forward_browser_messages(browser_queue))

    # 3) Port prompt
    raw = input(f"Enter your listening port (default {DEFAULT_PORT}): ").strip()
    port = int(raw) if raw else DEFAULT_PORT

    # 4) Start listener
    start_connection_listener(port)

    # 5) Connection mode
    print("\n1) LAN discovery\n2) ngrok tunnel\n3) Quit chat")
    choice = input("Choose [1/2/3]: ").strip() or "1"
    if choice == "3":
        raise RestartChatException()

    if choice == "1":
        start_discovery(port)
        print(f"[*] LAN discovery on port {port}")
    else:
        try:
            from pyngrok import ngrok
            token = os.getenv("NGROK_AUTH_TOKEN", "").strip()
            if not token:
                token = input("Enter your ngrok authtoken (or press Enter to skip): ").strip()
            if token:
                ngrok.set_auth_token(token)
                tunnel = ngrok.connect(port, "tcp")
                msg = f"[*] ngrok public tunnel at {tunnel.public_url}"
                print(msg)
                broadcast_to_browsers(msg)
            else:
                print("[*] Skipped ngrok; peers must /connect via LAN IP")
        except ImportError:
            print("[!] pyngrok not installed; skipping public tunnel.")
        except Exception as e:
            print(f"[!] ngrok error: {e}")

    # 6) Go!
    print("\n[*] Ready – type your message or /help\n")
    prompt_and_send_messages()
