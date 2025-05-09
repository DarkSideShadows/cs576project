import os, asyncio
from aiohttp import web, WSMsgType

app = web.Application()
connected_ws     = set()
from_browser_q   = None
_ui_loop         = None

def set_from_browser_queue(q: asyncio.Queue):
    global from_browser_q
    from_browser_q = q

def set_ui_loop(loop: asyncio.AbstractEventLoop):
    global _ui_loop
    _ui_loop = loop

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_ws.add(ws)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                # broadcast to other browsers
                for c in connected_ws:
                    if c is not ws:
                        await c.send_str(msg.data)
                # deliver to Python
                if from_browser_q:
                    await from_browser_q.put(msg.data)
    finally:
        connected_ws.remove(ws)
    return ws

def broadcast_to_browsers(line: str):
    if _ui_loop is None:
        return
    # schedule sends on the UI loop
    for ws in connected_ws:
        def _send(ws=ws, line=line):
            asyncio.create_task(ws.send_str(line))
        _ui_loop.call_soon_threadsafe(_send)

# routing
app.router.add_get('/',      lambda r: web.FileResponse(os.path.join('web','index.html')))
app.router.add_get('/ws',    websocket_handler)
app.router.add_static('/static/', path='web', name='static')