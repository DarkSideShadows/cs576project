# P2P Chat

A decentralized, peer-to-peer messaging app built in Python with encrypted communication, LAN discovery, and terminal-based messaging (for now).

---

## Project Structure
```
p2p-chat/
├── main.py 			# Entry point
├── core/
│ ├── peer.py 			# P2P messaging logic (connections, handshake, browser integration)
│ ├── discovery.py 		# Peer discovery over LAN (UDP)
│ ├── commands.py 		# Command handling logic
│ ├── config.py 		# Constants (buffer size, ports)
│ ├── utils.py 			# Local IP handling, socket helpers
├── crypto/
│ ├── crypto_utils.py 	# RSA key generation + encryption
├── web/
│ ├── index.html 		# Chat frontend (WebSocket UI)
├── bridge.py 			# WebSocket bridge for browser ↔ backend
├── requirements.txt
├── README.md
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/DarkSideShadows/cs576project.git
cd p2p-chat
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
python main.py
```

The app launches in your browser at http://127.0.0.1:8080.
You’ll be prompted for:

    Nickname

    Port (default: 5000)

    Connection mode (LAN or ngrok)

Peers on the same network auto-discover. Otherwise, connect manually or share your ngrok tunnel.

---

## Available Commands

| Command     | Description                                |
|-------------|--------------------------------------------|
| `/help`     | Show available commands                    |
| `/peers`    | List connected peers                       |
| `/me`       | Send a third-person message                |
| `/clear`    | Clear the terminal screen                  |
| `/quit`     | Disconnect and exit                        |

---
