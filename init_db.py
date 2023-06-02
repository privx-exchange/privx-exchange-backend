import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from db.models import *


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    psqlurl = os.environ.get("PSQLURL")
    engine = create_engine(psqlurl)
    session = sessionmaker(bind=engine)()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
