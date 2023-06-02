import os
import asyncio
from db import Database



async def run():
    psqlurl = os.environ.get("PSQLURL")
    global db
    db = Database(psqlurl)
    while True:
        print('match orders-----------------')
        db.match_orders()
        await asyncio.sleep(10)
