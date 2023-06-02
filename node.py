import aiohttp
import os
import asyncio
from db import Database


async def run():
    global db
    psqlurl = os.environ.get("PSQLURL")
    db = Database(psqlurl)
    node_host = os.environ.get("NODE_HOST", 'http://127.0.0.1:3030')

    async with aiohttp.ClientSession() as session:
        while True:
            print('sync block-----------------')
            async with session.get(f"{node_host}/testnet3/latest/height") as resp:
                if not resp.ok:
                    print("failed to get latest height")
                    continue
                latest_height = int(await resp.text())
                local_height = db.get_db_height()
                while latest_height > local_height:
                    print("remote latest height:", latest_height)
                    start = local_height + 1
                    end = min(start + 50, latest_height + 1)
                    print(f"fetching blocks {start} to {end - 1}")
                    async with session.get(f"{node_host}/testnet3/blocks?start={start}&end={end}") as block_resp:
                        if not block_resp.ok:
                            print("failed to get blocks")
                            continue
                        for block in await block_resp.json():
                            local_height = db.save_block(block)
            await asyncio.sleep(10)


if __name__ == '__main__':
    pass
