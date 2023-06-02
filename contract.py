import os
import aiohttp
import asyncio
from db import Database


async def run():
    psqlurl = os.environ.get("PSQLURL")
    private_key = os.environ.get('PRIVATE_KEY')
    contract_name = os.environ.get("CONTRACT_NAME", 'privx_xyz.aleo')
    global db
    db = Database(psqlurl)

    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(2)
            trade = db.get_offchain_trade_pair()
            if not trade:
                continue

            print('call contract to onchain trades-----------------')
            contract_url = f"{os.environ.get('CONTRACT_HOST')}/testnet3/execute"
            if trade['token_id'] == 1:
                program_function = "knockdown"
            else:
                program_function = "knockdown_2"
            data = dict(
                program_id=contract_name,
                program_function=program_function,
                inputs=[f"{trade['buy_order_id']}u64", f"{trade['sell_order_id']}u64"],
                private_key=private_key,
                fee=1000,
            )
            async with session.post(url=contract_url, json=data) as resp:
                if not resp.ok:
                    print("failed to call contract")
                    print(contract_url)
                    print(resp.status)
                    print(await resp.text())
                    continue

            db.onchain_trade(trade['id'])
