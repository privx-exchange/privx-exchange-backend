import datetime
import pandas as pd
from io import StringIO
from sqlalchemy import func, or_
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Block, Order, Trade


def u64(num):
    if num.endswith('u64'):
        return int(num[:-3])


class Database:
    def __init__(self, psqlurl):
        self.engine = create_engine(psqlurl)
        self.session = sessionmaker(bind=self.engine)()

    def get_db_height(self):
        height = self.session.query(func.max(Block.height)).first()[0]
        if height is None:
            return -1
        return height


    def load_valid_orders(self, filter=None):
        query = self.session.query(Order).order_by(Order.id)
        if filter:
            query = query.filter_by(**filter)
        orders = query.all()
        return [dict(trade_id=i.id, type=i.type, side=i.side, quantity=i.quantity, origin_quantity=i.origin_quantity,
                    price=i.price, addr=i.addr, 
                    height=i.height, created_at=i.created_at, updated_at=i.updated_at,
                    status=i.status,
                    ) for i in orders]

    def load_prices(self):
        query = self.session.query(Order).filter_by(status='todo')
        data = {}
        ret = []
        for order in query.all():
            key = f'{order.side}+{order.price}'
            if key in data:
                data[key] += order.quantity
            else:
                data[key] = order.quantity
        for k,v in data.items():
            side, price = k.split('+')
            ret.append(dict(side=side, price=float(price), quantity=v))
        return ret

    def get_offchain_trade_pair(self):
        trade = self.session.query(Trade).filter_by(onchain=False).first()
        if trade:
            if trade.party1_order.side == 'ask':
                return dict(id=trade.id, sell_order_id=trade.party1_order.id, buy_order_id=trade.party2_order.id)
            else:
                return dict(id=trade.id, sell_order_id=trade.party2_order.id, buy_order_id=trade.party1_order.id)
        return trade

    def onchain_trade(self, trade_id):
        self.session.query(Trade).filter(Trade.id == trade_id).update({Trade.onchain:True})
        self.session.commit()

    def load_trades(self, symbol=None, tm_from=None, tm_to=None, onchain=None, addr=None, order_id=None):
        query = self.session.query(Trade)
        if symbol is not None:
            query = query.filter(Trade.symbol==symbol)
        if tm_from is not None:
            query = query.filter(Trade.created_at >= tm_from)
        if tm_to is not None:
            query = query.filter(Trade.created_at <= tm_to)
        if onchain is not None:
            query = query.filter(Trade.onchain == onchain)
        if addr is not None:
            query = query.filter(or_(Trade.party1_order.has(addr=addr), Trade.party2_order.has(addr=addr)))
        if order_id is not None:
            query = query.filter(or_(Trade.party1_order.has(id=order_id), Trade.party2_order.has(id=order_id)))
        trades = query.all()
        return [dict(id=i.id, price=i.price, quantity=i.quantity,
                    orders=[
                        dict(trade_id=i.party1_order.id, type=i.party1_order.side, price=i.party1_order.price, addr=i.party1_order.addr),
                        dict(trade_id=i.party2_order.id, type=i.party2_order.side, price=i.party2_order.price, addr=i.party1_order.addr),
                    ],
                    left=i.party1_order.quantity,
                    left_origin=i.party1_order.origin_quantity,
                    right=i.party2_order.quantity,
                    right_origin=i.party2_order.origin_quantity,
                    onchain=i.onchain,
                    created_at=i.created_at,
                    updated_at=i.updated_at,
                    ) for i in trades]

    def summary_trade(self, symbol=None):
        now = datetime.datetime.now()
        tm_from = now - datetime.timedelta(days=1)
        query = self.session.query(Trade).filter(Trade.created_at >= tm_from)
        if symbol is not None:
            query = query.filter(Trade.symbol==symbol)

        volume_24h = 0
        high_24h = 0
        low_24h = 0
        quantity_24h = 0
        for trade in query.all():
            volume_24h += trade.quantity * float(trade.price)
            quantity_24h += trade.quantity
            if high_24h == 0:
                high_24h = trade.price
            if low_24h == 0:
                low_24h = trade.price
            if trade.price < low_24h:
                low_24h = trade.price
            if trade.price > high_24h:
                high_24h = trade.price
        return dict(
            volume_24h=volume_24h,
            high_24h=high_24h,
            low_24h=low_24h,
            quantity_24h=quantity_24h,
        )

    def load_history(self, symbol=None, tm_from=None, tm_to=None, resolution='15Min'):
        query = self.session.query(Trade)
        if symbol:
            query = query.filter(Trade.symbol==symbol)
        if tm_from:
            query = query.filter(Trade.created_at >= tm_from)
        if tm_to:
            query = query.filter(Trade.created_at <= tm_to)
        trades = query.all()

        data = ''
        for trade in trades:
            data += f'{trade.created_at.strftime("%Y-%m-%d %H:%M:%S")},{trade.price},{trade.quantity}\n'

        data = pd.read_csv(StringIO(data), names=['Date_Time', 'LTP', 'LTQ'], index_col=0)
        # Convert the index to datetime
        data.index = pd.to_datetime(data.index, format='%Y-%m-%d %H:%M:%S')
        resample_LTP = data['LTP'].resample(resolution).ohlc()
        resample_LTQ = data['LTQ'].resample(resolution).sum()
        return dict(s='ok',
                    t=[int(i.astype('datetime64[s]').astype('int')) for i in resample_LTP.index.values],
                    o=list(resample_LTP['open'].fillna(0).values),   # or .to_numpy()
                    h=list(resample_LTP['high'].fillna(0).values),
                    l=list(resample_LTP['low'].fillna(0).values),
                    c=list(resample_LTP['close'].fillna(0).values),
                    v=list(resample_LTQ.values),
                    )

    def save_block(self, block):
        height = block['header']['metadata']['height']
        created_at = datetime.datetime.fromtimestamp(block['header']['metadata']['timestamp'])
        self.session.add(Block(height=height))
        for transaction in block['transactions']:
            if transaction['status'] != 'accepted' or transaction['type'] != 'execute':
                continue
            for transition in transaction['transaction']['execution']['transitions']:
                if transition['program'] == 'privx_xyz.aleo' and transition['function'] == 'sell':
                    print(height, 'sell')
                    addr, quantity, price = transition['finalize']
                    self.session.add(Order(side='ask', price=u64(price), quantity=u64(quantity), origin_quantity=u64(quantity), addr=addr, height=height, created_at=created_at))
                if transition['program'] == 'privx_xyz.aleo' and transition['function'] == 'buy':
                    print(height, 'buy')
                    addr, quantity, price = transition['finalize']
                    self.session.add(Order(side='bid', price=u64(price), quantity=u64(quantity), origin_quantity=u64(quantity), addr=addr, height=height, created_at=created_at))
        self.session.commit()
        return height

    def match_orders(self):
        orders = self.load_valid_orders({'status': 'todo'})
        from orderbook import OrderBook
        match_engine = OrderBook()
        for o in orders:
            trades, order_left = match_engine.process_order(o, False, False)
            if len(trades) == 0:
                continue

            if order_left is None:
                self.session.query(Order).filter(Order.id == o['trade_id']).update({Order.status:'done', Order.quantity:0})
            else:
                self.session.query(Order).filter(Order.id == o['trade_id']).update({Order.quantity: order_left['quantity']})

            for t in trades:
                if t['party1'][3] is None:
                    self.session.query(Order).filter(Order.id == t['party1'][0]).update({Order.status:'done', Order.quantity:0})
                else:
                    self.session.query(Order).filter(Order.id == t['party1'][0]).update({Order.quantity:t['party1'][3]})
                self.session.add(Trade(price=t['price'], quantity=t['quantity'], party1_order_id=t['party1'][0], party2_order_id=t['party2'][0]))

            self.session.commit()
