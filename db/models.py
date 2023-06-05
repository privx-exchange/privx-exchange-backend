from datetime import datetime
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Sequence
import sqlalchemy.types as types


Base = declarative_base()


class ChoiceType(types.TypeDecorator):

    impl = types.String

    def __init__(self, choices, **kw):
        self.choices = dict(choices)
        super(ChoiceType, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        result = [k for k, v in self.choices.items() if v == value]
        if result:
            return result[0]
        else:
            return None

    def process_result_value(self, value, dialect):
        return self.choices[value]


class Block(Base):
    __tablename__ = 'block'

    height = sqlalchemy.Column(sqlalchemy.INTEGER, primary_key=True)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)



class Order(Base):
    __tablename__ = 'order'

    id = sqlalchemy.Column(sqlalchemy.INTEGER, Sequence('order_id_seq', minvalue=0, start=0, increment=1), primary_key=True, autoincrement=True) # start from 0
    type = sqlalchemy.Column(ChoiceType({"limit": "limit", "market": "market"}), nullable=False, default='limit')
    side = sqlalchemy.Column(ChoiceType({"ask": "ask", "bid": "bid"}), nullable=False, default='ask')
    quantity = sqlalchemy.Column(sqlalchemy.INTEGER)
    origin_quantity = sqlalchemy.Column(sqlalchemy.INTEGER)
    price = sqlalchemy.Column(sqlalchemy.DECIMAL)
    addr = sqlalchemy.Column(sqlalchemy.String(100))
    status = sqlalchemy.Column(ChoiceType({"todo": "todo", "done": "done", "cancel": "cancel"}), nullable=False, default='todo')
    height = sqlalchemy.Column(sqlalchemy.INTEGER, default=0)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    __tablename__ = 'trade'

    id = sqlalchemy.Column(sqlalchemy.INTEGER, primary_key=True)
    price = sqlalchemy.Column(sqlalchemy.DECIMAL)
    quantity = sqlalchemy.Column(sqlalchemy.FLOAT)
    party1_order_id = sqlalchemy.Column(sqlalchemy.INTEGER, sqlalchemy.ForeignKey("order.id"))
    party2_order_id = sqlalchemy.Column(sqlalchemy.INTEGER, sqlalchemy.ForeignKey("order.id"))
    party1_order = relationship('Order', foreign_keys=[party1_order_id], backref='trades_pt1')
    party2_order = relationship('Order', foreign_keys=[party2_order_id], backref='trades_pt2')
    created_at = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    onchain = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
