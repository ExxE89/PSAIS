import collections
import datetime
import logging
import os
import time

import elasticsearch
import ruamel.yaml as yaml
import yahoo_finance


OFF_DAY_INTERVAL = 3600
StockInfo = collections.namedtuple("StockInfo", ("symbol", "price", "date"))


def fetch_stock_info(ticker_symbol):
    logger.debug("Fetching {} data ...".format(ticker_symbol))
    now = datetime.datetime.utcnow()
    share = yahoo_finance.Share(ticker_symbol)
    price = share.get_price()
    
    try:
        price = float(price)
    except ValueError:
        logger.error("Cannot parse {} price as float: {}".format(ticker_symbol, price))
        price = None
    else:
        logger.debug("{} current price: {}".format(ticker_symbol, price))
    
    stock_info = StockInfo(symbol=ticker_symbol, price=price, date=now)
    return stock_info


def get_config():
    config_file = os.getenv("SCRAPER_CONFIG", "config.yaml")
    config_file = os.path.abspath(config_file)
    
    logger.debug("Using config file at {}".format(config_file))
    
    with open(config_file) as fh:
        content = fh.read()
    
    config = yaml.load(content)
    return config


def get_database(host):
    logger.debug("Connecting to database ...")
    db = elasticsearch.Elasticsearch(host)
    db.ping()
    logger.debug("Database connection successful")
    return db


def get_fetch_pause(config):
    now = datetime.datetime.now()
    day = now.weekday()
    
    if day in (5, 6):
        logger.info("It is currently not a weekday. Setting sleep duration to {} seconds".format(OFF_DAY_INTERVAL))
        return OFF_DAY_INTERVAL
    
    return config["scraper"]["interval_s"]


def get_logger():
    logger = logging.getLogger("psais.scraper.yahoo.finance")
    logger.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    
    logger.addHandler(ch)
    
    return logger


def main():
    config = get_config()
    logger.setLevel(config["log_level"])
    
    if config["scraper"]["save_data"]:
        db = get_database(config["database"]["host"])
    else:
        db = None
    
    start_scrape_loop(db, config)


def save_stock_info(db, stock_info):
    logger.debug("Saving stock info to database")
    
    body = {
        "ticker_symbol": stock_info.symbol,
        "date": stock_info.date,
        "price": stock_info.price,
    }
    
    db.index(index="stock_data", doc_type="stock_price", body=body)


def start_scrape_loop(db, config):
    while True:
        for ticker_symbol in config["scraper"]["ticker_symbols"]:
            stock_info = fetch_stock_info(ticker_symbol)
            
            if config["scraper"]["save_data"] and stock_info.price:
                save_stock_info(db, stock_info)
        
        duration = get_fetch_pause(config)
        logger.debug("Sleeping for {} s ...".format(duration))
        time.sleep(duration)


logger = get_logger()

if __name__ == "__main__":
    main()
