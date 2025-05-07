# core/peer.py
# Coordinates peer discovery, secure handshake, and message I/O

import socket
import threading
import time
import os
import asyncio
from datetime import datetime

from core.discovery import start_discovery, get_active_peers
from core.utils import get_all_local_ips
from core.config import DEFAULT_PORT, BUFFER
from core.commands import handle_command
from crypto.crypto_utils import (
    generate_key_pair,
    serialize_public_key,
    deserialize_public_key,
    encrypt_message,
    decrypt_message
)

# -----------------------------
# Global State
# -----------------------------
connections      = []       # active TCP connections
conn_peer_map    = {}       # {socket: peer_id}  # NEW
peer_public_keys = {}       # {peer_id: public_key}
connected_ids    = set()    # to avoid duplicate connections

peer_names = {}             # {peer_id: nickname}
my_name    = ""             # set at startup

LOCAL_IPS, _ = get_all_local_ips(), None  # discover local IPs

# generate our RSA keypair
my_private_key, my_public_key = generate_key_pair()

# -----------------------------
# Connection Handling
# -----------------------------
def start_connection_listener(listen_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', listen_port))
    s.listen()
    print(f"[*] Listening for incoming peer connections on port {listen_port}...")

    def _accept_loop():
        while True:
            try:
                conn, addr = s.accept()
                accept_incoming_connections(conn, addr)
            except Exception as e:
                print(f"[!] Listener error: {e}")
                break

    threading.Thread(target=_accept_loop, daemon=True).start()


def accept_incoming_connections(conn, addr):
    perform_handshake(conn, addr, is_incoming=True)


def initiate_peer_connections(host, listen_port):
    """
    Outgoing: connect to `host:listen_port` if not already connected.
    `host` may be a hostname (e.g. ngrok.io) or IP.
    """
    if host in connected_ids:
        print(f"[!] Already connected to {host}, skipping.")
        return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, listen_port))
        perform_handshake(s, (host, listen_port), is_incoming=False)
    except Exception as e:
        print(f"[!] Connection attempt to {host}:{listen_port} failed: {e}")


def perform_handshake(sock, addr, is_incoming):
    """
    Exchange public keys & nicknames. Key everything by the
    same `peer_id` you’ll use when sending messages.

    This sets up trust (RSA public keys), enables end-to-end encryption,
    and registers peers in the system so messages can be routed and decrypted properly.
    """
    # Determine canonical peer_id:
    # TODO: could be replaced with a public key hash later
    if is_incoming:
        # For incoming, use the actual connecting IP
        peer_id = sock.getpeername()[0]
    else:
        # For outgoing, use the hostname string (addr[0])
        peer_id = addr[0]

    try:
        # 1) Exchange keys
        if is_incoming:
            # receive first, then send
            peer_pubkey_bytes = sock.recv(BUFFER)
            peer_public_keys[peer_id] = deserialize_public_key(peer_pubkey_bytes)
            sock.sendall(serialize_public_key(my_public_key))
        else:
            # send first, then receive
            sock.sendall(serialize_public_key(my_public_key))
            peer_pubkey_bytes = sock.recv(BUFFER)
            peer_public_keys[peer_id] = deserialize_public_key(peer_pubkey_bytes)

        # 2) Exchange names
        if is_incoming:
            their_name = sock.recv(BUFFER).decode().strip()
            sock.sendall(my_name.encode())
        else:
            sock.sendall(my_name.encode())
            their_name = sock.recv(BUFFER).decode().strip()

        # 3) Record state
        peer_names[peer_id]    = their_name or peer_id
        connections.append(sock)
        conn_peer_map[sock]    = peer_id     # NEW
        connected_ids.add(peer_id)
        print(f"[+] Secure connection established with {peer_names[peer_id]} ({peer_id})")

        # 4) Start message listener
        threading.Thread(target=listen_for_messages, args=(sock, peer_id), daemon=True).start()

    except Exception as e:
        print(f"[!] Failed to set up connection with {peer_id}: {e}")
        sock.close()


# -----------------------------
# Communication Loops
# -----------------------------
def listen_for_messages(sock, peer_id):
    while True:
        try:
            data = sock.recv(BUFFER)
        except:
            break
        if not data:
            # peer closed
            name = peer_names.pop(peer_id, peer_id)
            print(f"[*] Connection to {name} ({peer_id}) closed.")

            connections.remove(sock)            # remove socket from connections
            peer_public_keys.pop(peer_id, None) # remove peer name and key
            conn_peer_map.pop(sock, None)       # remove socket-peer map
            connected_ids.discard(peer_id)      # remove from connected ids
            sock.close()
            break
        try:
            msg = decrypt_message(my_private_key, data)
            timestamp = datetime.now().strftime('%H:%M')
            print(f"\n[{timestamp}] {peer_names.get(peer_id,peer_id)}: {msg}")
        except Exception as e:
            print(f"[!] Decryption error from {peer_id}: {e}")


def prompt_and_send_messages():
    while True:
        msg = input()
        if msg.startswith('/'):
            handle_command(msg, my_name, connections, peer_names, peer_public_keys)
            continue

        timestamp = datetime.now().strftime('%H:%M')
        print(f"[{timestamp}] You: {msg}")

        # encrypt and send to all peers
        for conn in list(connections):
            peer_id = conn_peer_map.get(conn)
            if not peer_id or peer_id not in peer_public_keys:
                print(f"[!] No public key for {peer_id}, message not sent.")
                continue
            try:
                encrypted = encrypt_message(peer_public_keys[peer_id], msg)
                conn.sendall(encrypted)
            except Exception as e:
                print(f"[!] Encryption/send error to {peer_id}: {e}")
                connections.remove(conn)
                conn_peer_map.pop(conn, None)


async def forward_browser_messages(queue):
    while True:
        msg = await queue.get()
        timestamp = datetime.now().strftime('%H:%M')
        print(f"[{timestamp}] [Browser] You: {msg}")


# -----------------------------
# Main Entry Point
# -----------------------------
async def start_chat_node(browser_queue=None):
    global my_name
    my_name = input("Enter your nickname: ").strip() or "Anonymous"

    if browser_queue:
        asyncio.create_task(forward_browser_messages(browser_queue))

    listen_port = int(input(f"Enter your listening port (default {DEFAULT_PORT}): ") or DEFAULT_PORT)
    threading.Thread(target=start_connection_listener, args=(listen_port,), daemon=True).start()

    start_discovery(listen_port)

    def connect_to_peers():
        while True:
            for ip, port in get_active_peers():
                if ip in LOCAL_IPS or ip.startswith("127.") or ip in connected_ids:
                    continue
                print(f"[Discovery] Connecting to {ip}:{port}")
                initiate_peer_connections(ip, port)
            time.sleep(5) # TODO: gradual backoff here

    threading.Thread(target=connect_to_peers, daemon=True).start()

    # announce how to reach you
    print(f"[*] Listening on port {listen_port}. You can be reached at:")
    for ip in LOCAL_IPS:
        print(f"    • {ip}:{listen_port}")

    # ngrok tunnel
    try:
        from pyngrok import ngrok # type: ignore
        token = os.environ.get("NGROK_AUTH_TOKEN", "").strip()
        if not token:
            token = input(
                "Enter your ngrok authtoken to enable public tunnel (or Enter to skip): "
            ).strip()
        if token:
            ngrok.set_auth_token(token)
            tunnel = ngrok.connect(listen_port, "tcp")
            public_url = tunnel.public_url # e.g. tcp://0.tcp.ngrok.io:12345
            print(f"[*] Public tunnel established at {public_url}")
            print("    • Use this address in /connect on remote peers.")
        else:
            print("[*] Skipping public ngrok tunnel (no authtoken provided).")
    except ImportError:
        print("[!] pyngrok not installed; skipping public tunnel.")
    except Exception as e:
        print(f"[!] ngrok error: {e}")

    print("[*] Type your message and press Enter to send.")
    print("[*] Type /help to see available commands.")
    threading.Thread(target=prompt_and_send_messages, daemon=True).start()