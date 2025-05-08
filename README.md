## TODO / Future Features
- [ ] GUI frontend (`gui/`)
- [ ] Blockchain-based message verification (`blockchain/`)
- [ ] Identity authentication and peer verification
- [ ] Private messaging channels (`/msg`)
- [ ] Connection resilience and reconnection logic

---

# P2P Chat

A decentralized, peer-to-peer messaging app built in Python with encrypted communication, LAN discovery, and terminal-based messaging (for now).

Additional notes (TODO): Cost of advertising? Decentralized user authentication or message verification? Blockchain usage?

---

## Project Structure
Idea for project structure (subject to change):
```
p2p-chat/
├── main.py                   # Entry point
├── core/
│   ├── peer.py               # Core P2P logic (Peer connection, encrypted messaging, and input/output loop)
│   ├── ephemeral.py          # Ephemeral messaging
│   ├── discovery.py          # Peer discovery (UDP)
│   ├── config.py             # Constants used across modules (port, buffer size, etc.)
│   ├── utils.py              # Reusable system-level helpers
├── crypto/
│   ├── crypto_utils.py       # RSA key generation, encryption, and serialization
├── gui/                      # (optional, for future GUI)
├── blockchain/               # (optional, for message chain or verification)
├── README.md
├── requirements.txt
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

Each peer should choose a unique nickname and port. Peers on the same network will auto-discover each other and exchange encrypted messages.

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
