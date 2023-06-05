import asyncio
import traceback

import api
import dealer
import node
import contract
from enum import IntEnum


class Message:
    class Type(IntEnum):
        NodeConnectError = 0
        NodeConnected = 1
        NodeDisconnected = 2

        DatabaseConnectError = 100
        DatabaseConnected = 101
        DatabaseDisconnected = 102
        DatabaseError = 103
        DatabaseBlockAdded = 104

    def __init__(self, type_: Type, data: any):
        self.type = type_
        self.data = data


class Explorer:

    def __init__(self):
        self.task = None
        self.message_queue = asyncio.Queue()
        self.node = None
        self.dev_mode = False
        self.latest_height = 0

    def start(self):
        self.task = asyncio.create_task(self.main_loop())

    async def message(self, msg: Message):
        await self.message_queue.put(msg)

    async def main_loop(self):
        try:
            asyncio.create_task(node.run())       # sync block to get order data
            asyncio.create_task(api.run())        # provide rest api
            asyncio.create_task(dealer.run())     # order match as trade
            asyncio.create_task(contract.run())   # upload trade to chain
            while True:
                msg = await self.message_queue.get()
                if msg.type == Message.Type.NodeConnectError:
                    print("node connect error:", msg.data)
                elif msg.type == Message.Type.NodeConnected:
                    print("node connected")
                elif msg.type == Message.Type.NodeDisconnected:
                    print("node disconnected")
                elif msg.type == Message.Type.DatabaseConnectError:
                    print("database connect error:", msg.data)
                elif msg.type == Message.Type.DatabaseConnected:
                    print("database connected")
                elif msg.type == Message.Type.DatabaseDisconnected:
                    print("database disconnected")
                elif msg.type == Message.Type.DatabaseError:
                    print("database error:", msg.data)
                elif msg.type == Message.Type.DatabaseBlockAdded:
                    # maybe do something later?
                    pass
                else:
                    raise ValueError("unhandled explorer message type")
        except Exception as e:
            print("explorer error:", e)
            traceback.print_exc()
            raise
