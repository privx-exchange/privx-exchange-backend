import asyncio
import contextlib
import datetime
import time
import threading
import os
import typing
import json
import logging
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from asgi_logger import AccessLoggerMiddleware

from db import Database


class HJSONResponse(JSONResponse):
    def render(self, content: typing.Any) -> bytes:
        content = dict(
            code=self.status_code,
            msg='',
            data=content,
        )
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")


class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


async def index_route(request):
    return HJSONResponse({'hello': 'world'})


async def order_route(request):
    filter = {}
    side = request.query_params.get('side')
    if side:
        filter['side'] = side
    status = request.query_params.get('status')
    if status:
        filter['status'] = status
    addr = request.query_params.get('addr')
    if addr:
        filter['addr'] = addr
    symbol = request.query_params.get('symbol')
    if symbol:
        filter['symbol'] = symbol
    tm_from = request.query_params.get('from')
    tm_to = request.query_params.get('to')
    if tm_from:
        tm_from = datetime.datetime.fromtimestamp(int(tm_from), datetime.timezone.utc)
        filter['tm_from'] = tm_from
    if tm_to:
        tm_to = datetime.datetime.fromtimestamp(int(tm_to), datetime.timezone.utc)
        filter['tm_to'] = tm_to
    orders = db.load_valid_orders(filter)
    return HJSONResponse(orders)


async def price_route(request):
    symbol = request.query_params.get('symbol')
    prices = db.load_prices(symbol=symbol)
    return HJSONResponse(prices)


async def trade_route(request):
    addr = request.query_params.get('addr')
    symbol = request.query_params.get('symbol')
    tm_from = request.query_params.get('tm_from')
    tm_to = request.query_params.get('tm_to')
    onchain = request.query_params.get('onchain')
    order_id = request.query_params.get('order_id')
    token_id = request.query_params.get('token_id')
    if onchain is not None:
        if onchain == 'true':
            onchain = True
        else:
            onchain = False
    trades = db.load_trades(symbol=symbol, tm_from=tm_from, tm_to=tm_to, onchain=onchain, addr=addr, order_id=order_id, token_id=token_id)
    return HJSONResponse(trades)


async def history_route(request):
    symbol = request.query_params.get('symbol')
    tm_from = request.query_params.get('from')
    tm_to = request.query_params.get('to')
    resolution = request.query_params.get('resolution', '15Min')
    if tm_from:
        tm_from = datetime.datetime.fromtimestamp(int(tm_from), datetime.timezone.utc)
    if tm_to:
        tm_to = datetime.datetime.fromtimestamp(int(tm_to), datetime.timezone.utc)
    if resolution.isdigit():
        resolution += 'Min'
    history = db.load_history(symbol=symbol, tm_from=tm_from, tm_to=tm_to, resolution=resolution)
    history['nextTime'] = request.query_params.get('from')
    return HJSONResponse(history)


async def summary_route(request):
    symbol = request.query_params.get('symbol')
    data = db.summary_trade(symbol)
    return HJSONResponse(data)


async def time_route(request):
    now = datetime.datetime.now()
    return HJSONResponse(int(now.timestamp()))


async def symbol_route(request):
    symbol = request.query_params.get('symbol', 'LEO-USDT')
    return HJSONResponse({
        "name": symbol,
        "timezone": "Asia/Singapore",
        "pricescale": 1,   #k data decimal
        "session": "24x7", #trade time window
        "supported_resolutions": [
            "1",
            "5",
            "15",
            "30",
            "60",
            "1D",
            "1W",
        ]})


async def symbols_route(request):
    tokens = db.load_tokens()
    return HJSONResponse(tokens)


async def bad_request(request: Request, exc: HTTPException):
    return HJSONResponse({}, status_code=400)


async def not_found(request: Request, exc: HTTPException):
    return HJSONResponse({}, status_code=404)


async def internal_error(request: Request, exc: HTTPException):
    return HJSONResponse({}, status_code=500)


routes = [
    Route("/", index_route),
    Route("/api/order", order_route),
    Route("/api/trade", trade_route),
    Route("/api/price", price_route),
    Route("/api/history", history_route),
    Route("/api/summary", summary_route),
    Route("/api/time", time_route),
    Route("/api/symbol", symbol_route),
    Route("/api/symbols", symbols_route),
]

exc_handlers = {
    400: bad_request,
    404: not_found,
    550: internal_error,
}

async def startup():
    async def noop(_): pass
    psqlurl = os.environ.get("PSQLURL")
    global db
    db = Database(psqlurl)


AccessLoggerMiddleware.DEFAULT_FORMAT = '\033[92mACCESS\033[0m: \033[94m%(client_addr)s\033[0m - - %(t)s \033[96m"%(request_line)s"\033[0m \033[93m%(s)s\033[0m %(B)s "%(f)s" "%(a)s" %(L)s'
app = Starlette(
    debug=True if os.environ.get("DEBUG") else False,
    routes=routes,
    on_startup=[startup],
    exception_handlers=exc_handlers,
    middleware=[Middleware(AccessLoggerMiddleware), Middleware(CORSMiddleware, allow_origins=['*'])]
)


async def run():
    config = uvicorn.Config("api:app", reload=True, log_level="info", host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get("PORT", 8000)))
    logging.getLogger("uvicorn.access").handlers = []
    server = Server(config=config)

    with server.run_in_thread():
        while True:
            await asyncio.sleep(3600)


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    uvicorn.run(app, host='0.0.0.0', port=8000)
