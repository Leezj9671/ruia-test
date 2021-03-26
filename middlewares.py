from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector
from ruia import Middleware, Request

middleware = Middleware()


@middleware.request
async def random_header(spider_ins, request: Request):
    ua = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36'
    headers = {
        'authority': 'www.facebook.com',
        'cache-control': 'no-cache',
        'upgrade-insecure-requests': '1',
        'user-agent': ua,
        'User-Agent': ua,
        'accept': '*/*',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'empty',
        'referer': 'https://www.facebook.com/pages/category/',
        'Origin': 'https://www.facebook.com',
        'Referer': 'https://www.facebook.com/',
        'Host': 'www.facebook.com',
        'origin': 'https://www.facebook.com',
        'pragma': 'no-cache',
    }
    request.headers.update(headers)


@middleware.request
async def request_proxy(spider_ins, request: Request):
    """request proxy"""
    connector = ProxyConnector.from_url('socks5://127.0.0.1:9999')
    request.request_session = ClientSession(connector=connector)
    request.close_request_session = True
