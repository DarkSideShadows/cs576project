import os
import asyncio
from aiohttp import web, WSMsgType

# ─── compute absolute path to web/ ─────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
WEB_DIR  = os.path.join(BASE_DIR, 'web')

# ─── WebSocket state & mailbox ──────────────────────────────────────────────
connected_clients = set()      # set of WebSocketResponse
from_browser_queue: asyncio.Queue = None

def set_from_browser_queue(q: asyncio.Queue):
    """Give us a queue on which the browser handler will .put() incoming texts."""
    global from_browser_queue
    from_browser_queue = q

def broadcast_to_browsers(msg: str):
    """Send a server-side string out to **all** connected browser UIs."""
    for ws in connected_clients:
        # schedule it on aiohttp's loop
        asyncio.get_event_loop().create_task(ws.send_str(msg))

# ─── HTTP handler: serve web/index.html ────────────────────────────────────
async def index(request):
    return web.FileResponse(os.path.join(WEB_DIR, 'index.html'))

# ─── WS handler: browser ↔ server ↔ peer-queue ──────────────────────────────
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)
    print("[*] Web client connected")

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                text = msg.data.strip()
                # echo to other browsers
                for other in connected_clients:
                    if other is not ws:
                        await other.send_str(text)
                # hand off to peer network
                if from_browser_queue:
                    await from_browser_queue.put(text)
            elif msg.type == WSMsgType.ERROR:
                print(f"[!] WebSocket error: {ws.exception()}")
    finally:
        connected_clients.remove(ws)
        print("[*] Web client disconnected")

    return ws

# ─── assemble & export the aiohttp application ─────────────────────────────
app = web.Application()
app.router.add_get('/',      index)
app.router.add_get('/ws',    websocket_handler)
app.router.add_static(
    '/static/',               # prefix (unused here, but available)
    path=WEB_DIR,             # serve all static from your ./web folder
    name='static'
)
