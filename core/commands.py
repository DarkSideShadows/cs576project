# core/commands.py
import os
from datetime import datetime
from crypto.crypto_utils import encrypt_message

class RestartChatException(Exception): pass
class ExitProgramException(Exception): pass

def handle_command(cmd, my_name, connections, peer_names, peer_public_keys, ui_broadcast):
    parts = cmd.strip().split(maxsplit=1)
    base  = parts[0]

    if base == "/help":
        lines = [
            "Available commands:",
            "/help        – show this",
            "/peers       – list peers",
            "/quit        – disconnect & restart",
            "/exit        – quit program",
            "/clear       – clear screen",
            "/me <action> – send a /me action",
            "/connect <ip> <port>",
            "/reconnect   – retry LAN discovery"
        ]
        ui_broadcast("\n".join(lines))

    elif base == "/peers":
        if not peer_names:
            out = "[*] No peers connected."
        else:
            out = "[*] Connected peers:\n" + "\n".join(f"{n} ({pid})" for pid,n in peer_names.items())
        ui_broadcast(out)

    elif base == "/quit":
        ui_broadcast("[*] Disconnecting and restarting…")
        raise RestartChatException()

    elif base == "/exit":
        ui_broadcast("[*] Exiting program. Goodbye!")
        raise ExitProgramException()

    elif base == "/clear":
        ui_broadcast("\x1b[2J\x1b[H")   # clear screen in HTML

    elif base == "/reconnect":
        from core.discovery import get_active_peers
        from core.peer      import initiate_peer_connections, LOCAL_IPS
        lines = ["[*] Reconnecting…"]
        for ip,port in get_active_peers():
            pid = f"{ip}:{port}"
            if pid not in peer_names and ip not in LOCAL_IPS:
                lines.append(f"→ {ip}:{port}")
                initiate_peer_connections(ip,port)
        ui_broadcast("\n".join(lines))

    elif base == "/connect":
        if len(parts)==2:
            try:
                host, raw = parts[1].split()
                port = int(raw)
                ui_broadcast(f"[*] Connecting to {host}:{port}")
                from core.peer import initiate_peer_connections
                initiate_peer_connections(host,port)
            except:
                ui_broadcast("[!] Usage: /connect <ip> <port>")
        else:
            ui_broadcast("[!] Usage: /connect <ip> <port>")

    elif base == "/me":
        if len(parts)<2:
            ui_broadcast("[!] Usage: /me <action>")
        else:
            action = f"* {my_name} {parts[1]}"
            ts = datetime.now().strftime("%H:%M")
            ui_broadcast(f"[{ts}] {action}")
            for sock,pid in connections:
                if pid in peer_public_keys:
                    try:
                        sock.sendall(encrypt_message(peer_public_keys[pid], action))
                    except:
                        pass

    else:
        ui_broadcast(f"[!] Unknown: {base}")
