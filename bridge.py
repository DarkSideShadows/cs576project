from aiohttp import web, WSMsgType
import os
import asyncio
from typing import Optional

connected_clients = set() # set of WebSocket connections
from_browser_queue: Optional[asyncio.Queue] = None # queue (mailbox) from browser -> p2p network

def set_from_browser_queue(queue: asyncio.Queue):
    global from_browser_queue
    from_browser_queue = queue

# serve index.html from the frontend folder
async def index(request):
    return web.FileResponse(os.path.join('frontend', 'index.html'))

# WebSocket handler for browser clients
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    print("[*] Web client connected")

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                # broadcast to all clients
                for client in connected_clients:
                    if client != ws:
                        await client.send_str(msg.data)

                # put message in mailbox -> send to p2p network (peer.py)
                if from_browser_queue:
                    await from_browser_queue.put(msg.data)
            elif msg.type == WSMsgType.ERROR:
                print(f"[!] WebSocket error: {ws.exception()}")
    finally:
        connected_clients.remove(ws)
        print("[*] Web client disconnected")

    return ws

# set up the app
app = web.Application()
app.router.add_get('/', index)
app.router.add_get('/ws', websocket_handler)
app.router.add_static('/static/', path='frontend', name='static')

if __name__ == '__main__':
    web.run_app(app, port=8080)