from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///./data/database.sqlite", echo=True)
session_factory = sessionmaker(engine, expire_on_commit=False)
