# core/commands.py
import os
from datetime import datetime
from crypto.crypto_utils import encrypt_message
from bridge import broadcast_to_browsers

# ─── Control-flow exceptions ─────────────────────────────────────────────────
class RestartChatException(Exception):
    """Raised to signal /quit → restart chat loop."""

class ExitProgramException(Exception):
    """Raised to signal /exit → tear down entirely."""

# ─── Command Dispatcher ────────────────────────────────────────────────────────
def handle_command(cmd, my_name, connections, peer_names, peer_public_keys):
    parts = cmd.strip().split(maxsplit=1)
    base  = parts[0]

    if base == "/help":
        lines = [
            "Available commands:",
            "/help        - show this message",
            "/peers       - list connected peers",
            "/quit        - disconnect & restart chat",
            "/exit        - terminate program",
            "/clear       - clear screen",
            "/me <action> - send a /me action",
            "/connect <ip> <port>",
            "/reconnect   - retry LAN discovery"
        ]
        out = "\n".join(lines)
        print(out)
        broadcast_to_browsers(out)

    elif base == "/peers":
        if not peer_names:
            out = "[*] No peers connected."
        else:
            out = "[*] Connected peers:\n" + "\n".join(
                f"{name} ({pid})" for pid,name in peer_names.items()
            )
        print(out)
        broadcast_to_browsers(out)

    elif base == "/quit":
        out = "[*] Disconnecting and restarting…"
        print(out)
        broadcast_to_browsers(out)
        raise RestartChatException()

    elif base == "/exit":
        out = "[*] Exiting program. Goodbye!"
        print(out)
        broadcast_to_browsers(out)
        raise ExitProgramException()

    elif base == "/clear":
        os.system('cls' if os.name=='nt' else 'clear')

    elif base == "/reconnect":
        from core.discovery import get_active_peers
        from core.peer      import initiate_peer_connections, connected_ids, LOCAL_IPS

        lines = ["[*] Reconnecting to known peers…"]
        for ip, port in get_active_peers():
            if ip not in connected_ids and ip not in LOCAL_IPS:
                lines.append(f"→ {ip}:{port}")
                initiate_peer_connections(ip, port)

        out = "\n".join(lines)
        print(out)
        broadcast_to_browsers(out)

    elif base == "/connect":
        if len(parts) == 2:
            try:
                host, raw = parts[1].split()
                port = int(raw)
                out = f"[*] Connecting to {host}:{port}"
                print(out)
                broadcast_to_browsers(out)
                from core.peer import initiate_peer_connections
                initiate_peer_connections(host, port)
            except:
                out = "[!] Usage: /connect <ip> <port>"
                print(out)
                broadcast_to_browsers(out)
        else:
            out = "[!] Usage: /connect <ip> <port>"
            print(out)
            broadcast_to_browsers(out)

    elif base == "/me":
        if len(parts) < 2:
            out = "[!] Usage: /me <action>"
            print(out)
            broadcast_to_browsers(out)
        else:
            action = f"* {my_name} {parts[1]}"
            ts     = datetime.now().strftime('%H:%M')
            line   = f"[{ts}] {action}"
            print(line)
            broadcast_to_browsers(line)
            for sock, pid in list(connections):
                if pid in peer_public_keys:
                    try:
                        enc = encrypt_message(peer_public_keys[pid], action)
                        sock.sendall(enc)
                    except:
                        pass

    else:
        out = f"[!] Unknown command: {base}"
        print(out)
        broadcast_to_browsers(out)
