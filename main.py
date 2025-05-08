import asyncio
import webbrowser
from aiohttp import web
from bridge import app, set_from_browser_queue
from core.peer import (
    start_chat_node,
    RestartChatException,
    ExitProgramException
)

async def start_everything():
    # 1) make a queue for Browser → P2P
    browser_q = asyncio.Queue()
    set_from_browser_queue(browser_q)

    # 2) spin up HTTP+WebSocket bridge on 0.0.0.0:8080
    runner = web.AppRunner(app)
    await runner.setup()
    site   = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()

    url = "http://127.0.0.1:8080"
    print(f"[*] Web UI running at {url}")
    webbrowser.open(url)

    # 3) now loop your chat-node, catching /quit vs /exit
    while True:
        try:
            # this will prompt for nickname, port, mode,
            # then block in prompt_and_send_messages() until you /quit or /exit
            await start_chat_node(browser_queue=browser_q)
        except RestartChatException:
            print("[*] Restarting chat…\n")
            continue
        except ExitProgramException:
            print("[*] Exiting program. Goodbye!")
            break

    # 4) tear down web server
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(start_everything())
