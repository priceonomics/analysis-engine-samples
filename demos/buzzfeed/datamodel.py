import sqlalchemy as db
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy.dialects.postgresql as psql_db

connection_string = 'postgresql://user:password@localhost/db' # substitute your own postgresql database here

Base = declarative_base()

class BuzzfeedIndex(Base):
    __tablename__ = 'buzzfeed_index'
    crawl_index = db.Column('crawl_index', db.Integer(), primary_key=True)
    crawl_date = db.Column(db.TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp())

class BuzzfeedArticle(Base):
    __tablename__ = 'buzzfeed_articles'
    id = db.Column('id', db.Integer(), primary_key=True)
    crawl_index = db.Column(db.Integer(), db.ForeignKey('buzzfeed_index.crawl_index'), index=True)
    created = db.Column(db.TIMESTAMP, server_default=func.now(), index=True)
    posted = db.Column(db.TIMESTAMP, index=True)
    title = db.Column(db.VARCHAR, index=True)
    url = db.Column(db.VARCHAR, index=True)
    social = db.Column(psql_db.JSON)
    sources = relationship('BuzzfeedSource', backref='article')

class BuzzfeedSource(Base):
    __tablename__ = 'buzzfeed_sources'
    id = db.Column('id', db.Integer(), primary_key=True)
    crawl_index = db.Column(db.Integer(), db.ForeignKey('buzzfeed_index.crawl_index'), index=True)
    created = db.Column(db.TIMESTAMP, server_default=func.now(), index=True)
    text = db.Column(db.VARCHAR, index=True)
    article_id = db.Column(db.Integer(), db.ForeignKey('buzzfeed_articles.id'), index=True)
    links = relationship('BuzzfeedLink', backref='source')

class BuzzfeedLink(Base):
    __tablename__ = 'buzzfeed_links'
    id = db.Column('id', db.Integer(), primary_key=True)
    crawl_index = db.Column(db.Integer(), db.ForeignKey('buzzfeed_index.crawl_index'), index=True)
    created = db.Column(db.TIMESTAMP, server_default=func.now(), index=True)
    url = db.Column(db.VARCHAR, index=True)
    source_id = db.Column(db.Integer(), db.ForeignKey('buzzfeed_sources.id'), index=True)

engine = db.create_engine(connection_string)
Base.metadata.create_all(engine)
