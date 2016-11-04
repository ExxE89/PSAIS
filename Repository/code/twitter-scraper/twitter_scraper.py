import datetime
import json
import logging
import os
import time

import elasticsearch
import langdetect
import ruamel.yaml as yaml
import tweepy


DOCUMENT_TYPE = "tweet"
INDEX_NAME = "twitter"


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


def get_logger():
    logger = logging.getLogger("psais.scraper.twitter")
    logger.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    
    logger.addHandler(ch)
    
    return logger


def get_parsed_tweet_time(tweet_time):
    time_struct = time.strptime(tweet_time, "%a %b %d %H:%M:%S +0000 %Y")
    time_datetime = datetime.datetime.fromtimestamp(time.mktime(time_struct))
    return time_datetime


def get_stream(db, config):
    listener = TweetStreamListener(db, config)

    auth = tweepy.OAuthHandler(config["twitter"]["consumer_key"], config["twitter"]["consumer_secret"])
    auth.set_access_token(config["twitter"]["access_token"], config["twitter"]["access_secret"])

    stream = tweepy.Stream(auth, listener)
    return stream


def main():
    config = get_config()
    logger.setLevel(config["log_level"])
    
    if config["scraper"]["save_tweets"]:
        db = get_database(config["database"]["host"])
    else:
        db = None
    
    stream = get_stream(db, config)

    stream.filter(track=config["scraper"]["track"])


def print_tweet(tweet):
    logger.debug("Tweet by {}: {}".format(tweet["user"]["screen_name"], tweet["text"]))


class TweetStreamListener(tweepy.streaming.StreamListener):
    def __init__(self, db, config):
        super().__init__()
        
        self.db = db
        self.languages = config["scraper"]["languages"]
        self.save_tweets = config["scraper"]["save_tweets"]
    
    def on_data(self, raw_data):
        try:
            self.process_tweet(raw_data)
        except Exception as e:
            logger.exception("Exception while processing tweet: {}".format(raw_data))
        
        return True

    def on_error(self, status):
        logger.error("Streaming error: {}".format(status))
    
    def process_tweet(self, raw_data):
        # Object structure: https://dev.twitter.com/overview/api/tweets
        tweet = json.loads(raw_data)
        
        print_tweet(tweet)
        
        try:
            language = langdetect.detect(tweet["text"])
        except langdetect.lang_detect_exception.LangDetectException:
            logger.info("Cannot detect language, skipping tweet")
            return
        
        logger.debug("Tweet language: {}".format(language))
        
        if self.save_tweets and language in self.languages:
            self.save_tweet(tweet)
    
    def save_tweet(self, tweet):
        logger.debug("Saving tweet to database")
        tweet_time = get_parsed_tweet_time(tweet["created_at"])
        
        body = {
            "author": tweet["user"]["screen_name"],
            "date": tweet_time,
            "message": tweet["text"],
        }
        
        self.db.index(
            index=INDEX_NAME,
            doc_type=DOCUMENT_TYPE,
            body=body,
        )


logger = get_logger()

if __name__ == "__main__":
    main()
