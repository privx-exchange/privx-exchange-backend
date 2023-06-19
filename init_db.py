import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from db.models import *


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    start_height = os.environ.get("START_HEIGHT", None)
    psqlurl = os.environ.get("PSQLURL")
    engine = create_engine(psqlurl)
    session = sessionmaker(bind=engine)()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session.add(Token(id=1, base="LEO", quote="TK1", symbol="TK1-LEO"))
    session.add(Token(id=2, base="LEO", quote="TK2", symbol="TK2-LEO"))

    if start_height and start_height.isdigit():
        session.add(Block(height=start_height))

    session.commit()
