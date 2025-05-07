import asyncio
import bridge
from core.peer import start_chat_node
from aiohttp import web

async def start_everything():
    # create the queue
    browser_to_peer_queue = asyncio.Queue()
    bridge.set_from_browser_queue(browser_to_peer_queue)

    # start the web server
    runner = web.AppRunner(bridge.app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("[*] Web server running at http://localhost:8080")

    # start peer backend
    await start_chat_node(browser_to_peer_queue)

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_everything())
