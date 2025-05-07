from aiohttp import web # type: ignore
import os

# serve index.html from the frontend folder
async def index(request):
    return web.FileResponse(os.path.join('frontend', 'index.html'))

app = web.Application()
app.router.add_get('/', index) # add a route when someone visits / (run index)
app.router.add_static('/static/', path='frontend', name='static')

if __name__ == '__main__':
    web.run_app(app, port=8080)