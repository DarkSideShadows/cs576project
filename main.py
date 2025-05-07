import asyncio, webbrowser
from aiohttp import web

from bridge import app, set_from_browser_queue, broadcast_to_browsers, set_ui_loop
from core.peer import set_ui_broadcaster, start_chat_node
from core.commands import RestartChatException, ExitProgramException

async def start_web_ui():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080)

    # capture the running loop for bridge broadcasts
    loop = asyncio.get_running_loop()
    set_ui_loop(loop)

    # hook Python→UI
    set_ui_broadcaster(broadcast_to_browsers)

    await site.start()
    url = "http://127.0.0.1:8080"
    print(f"[*] Web UI running at {url}")
    webbrowser.open(url, new=2)

async def main():
    # browser→Python
    browser_queue = asyncio.Queue()
    set_from_browser_queue(browser_queue)

    # start UI
    await start_web_ui()

    # run chat flow entirely in-browser
    try:
        await start_chat_node(browser_queue)
    except ExitProgramException:
        pass

if __name__ == "__main__":
    asyncio.run(main())
