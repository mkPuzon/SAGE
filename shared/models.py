import os
from sqlalchemy import Column, String, Integer, JSON, create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    paper_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    arxiv_url = Column(String)
    pdf_url = Column(String)
    date_submitted = Column(String)
    date_scraped = Column(String)
    tags = Column(JSON)
    abstract = Column(String)


class Keyword(Base):
    __tablename__ = "keywords"

    keyword = Column(String, primary_key=True)
    definition_simple = Column(String)
    definition_technical = Column(String)
    count = Column(Integer, default=0)
    paper_references = Column(JSON)
    dates = Column(JSON)


class KeywordCooccurrence(Base):
    __tablename__ = "keyword_cooccurrences"

    keyword_a = Column(String, primary_key=True)
    keyword_b = Column(String, primary_key=True)
    score = Column(Integer, default=0)


def get_engine(db_path: str):
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine
