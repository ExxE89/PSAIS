import collections
import logging
import os
import re
import time

import elasticsearch
import elasticsearch.helpers
import ruamel.yaml as yaml

import classifiers


BASEDIR = os.path.dirname(__file__)
CONTEXT_TIMEOUT = "1m"
DOCUMENT_TYPE = "tweet"
INDEX_NAME = "twitter"
REQUEST_TIMEOUT = 60
SCROLL_BATCH_SIZE = 1000
SPAM_FILTER_FILENAME = os.path.join(BASEDIR, "spam_filter.txt")
SPAM_FILTERS = []
UPDATE_CHUNK_SIZE = 2500
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

TweetDocument = collections.namedtuple("TweetDocument", ("id", "data"))


def get_classified_tweet(classifier, classifier_name, tweet):
    classification = classifier(tweet.data["message"])

    data = {
        "sentiment_{}".format(classifier_name): classification["polarity"],
    }

    return TweetDocument(id=tweet.id, data=data)


def get_classified_tweet_actions(db, config):
    classifier = get_classifier(config)
    
    tweets = get_tweets(db, config)
    tweets = filter(lambda x: not is_spam_tweet(x), tweets)
    tweets = map(get_url_filtered_tweet, tweets)
    
    for tweet in tweets:
        try:
            classified_tweet = get_classified_tweet(classifier, config["classifier"], tweet)
            action = get_save_action(db, classified_tweet)
            yield action
        except Exception:
            logger.exception("Error while processing tweet")


def get_classifier(config):
    return getattr(classifiers, config["classifier"]).classify


def get_config():
    config_file = os.getenv("SENTIMENT_CONFIG", "config.yaml")
    config_file = os.path.abspath(config_file)

    logger.debug("Using config file at {}".format(config_file))

    with open(config_file) as fh:
        content = fh.read()

    config = yaml.load(content)
    return config


def get_database(host):
    logger.debug("Connecting to database ...")
    db = elasticsearch.Elasticsearch(host, timeout=REQUEST_TIMEOUT)
    db.ping()
    logger.debug("Database connection successful")
    return db


def get_logger():
    logger = logging.getLogger("psais.scraper.yahoo.finance")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger


def get_save_action(db, tweet):
    return {
        "_op_type": "update",
        "_id": tweet.id,
        "_index": INDEX_NAME,
        "_type": DOCUMENT_TYPE,
        "doc": tweet.data,
    }


def get_tweets(db, config):
    logger.info("Initializing scroll search ...")

    response = db.search(
        index=INDEX_NAME,
        doc_type=DOCUMENT_TYPE,
        scroll=CONTEXT_TIMEOUT,
        search_type="scan",
        body={
            "query": config["search_filter"],
            "size": SCROLL_BATCH_SIZE,
        },
    )

    scroll_id = response["_scroll_id"]
    cur_count = response["hits"]["total"]

    logger.info("Streaming {} documents ...".format(cur_count))
    processed_count = 0

    while cur_count > 0:
        response = db.scroll(scroll_id=scroll_id, scroll=CONTEXT_TIMEOUT)
        cur_count = len(response["hits"]["hits"])
        scroll_id = response["_scroll_id"]

        processed_count += cur_count
        progress = processed_count / response["hits"]["total"] * 100
        remaining = response["hits"]["total"] - processed_count

        logger.info("{}/{} documents ({:.1f} %) fetched, {} remaining ...".format(
            processed_count,
            response["hits"]["total"],
            progress,
            remaining,
        ))

        for hit in response["hits"]["hits"]:
            yield TweetDocument(id=hit["_id"], data=hit["_source"])


def get_url_filtered_tweet(tweet):
    message = tweet.data["message"]
    message = URL_PATTERN.sub("", message)
    message = message.strip()
    
    tweet.data["message"] = message
    return tweet  # Not a new instance, I know.


def is_spam_tweet(tweet):
    for pattern in SPAM_FILTERS:
        if pattern.search(tweet.data["message"]):
            return True
    
    return False


def load_spam_filters():
    with open(SPAM_FILTER_FILENAME) as fh:
        for line in fh:
            line = line.strip()
            
            if not line:
                continue
            
            pattern = re.compile(line, re.IGNORECASE)
            SPAM_FILTERS.append(pattern)


def main():
    config = get_config()
    logger.setLevel(config["log_level"])
    db = get_database(config["database"]["host"])
    
    load_spam_filters()

    classified_tweets = get_classified_tweet_actions(db, config)
    elasticsearch.helpers.bulk(db, classified_tweets, chunk_size=UPDATE_CHUNK_SIZE)


logger = get_logger()

if __name__ == "__main__":
    main()
