import logging
import os
import sys
import time

BASEDIR = os.path.dirname(__file__)
INTERVAL_SECONDS = 15
SAVE_DELAY_SECONDS = 3
PRICE_PREDICTOR_PATH = os.path.join(BASEDIR, "..", "price-predictor")
SENTIMENT_ANALYZER_PATH = os.path.join(BASEDIR, "..", "sentiment-analyzer")

sys.path.append(PRICE_PREDICTOR_PATH)
sys.path.append(SENTIMENT_ANALYZER_PATH)

import aggregator
import price_predictor
import sentiment_analyzer


def init_aggregator():
    if not os.getenv("SENTIMENT_CONFIG"):
        os.environ["SENTIMENT_CONFIG"] = os.path.join(SENTIMENT_ANALYZER_PATH, "config.yaml")


def init_price_predictor():
    if not os.getenv("PRICE_CONFIG"):
        os.environ["PRICE_CONFIG"] = os.path.join(PRICE_PREDICTOR_PATH, "config.yaml")


def init_sentiment_analyzer():
    if not os.getenv("SENTIMENT_CONFIG"):
        os.environ["SENTIMENT_CONFIG"] = os.path.join(SENTIMENT_ANALYZER_PATH, "config.yaml")


def get_logger():
    logger = logging.getLogger("psais.autorefresher")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger


def run_aggregator():
    aggregator.main()


def run_price_predictor():
    price_predictor.main()


def run_sentiment_analyzer():
    sentiment_analyzer.main()


def main():
    init_aggregator()
    init_price_predictor()
    init_sentiment_analyzer()
    
    while True:
        logger.info("Running sentiment analyzer ...")
        if not os.getenv("SPARK"):
            run_sentiment_analyzer()
        else:
            os.system("bash " + os.path.join(SENTIMENT_ANALYZER_PATH, "spark-sentiment-analyzer.sh"))
        
        logger.info("Running aggregator ...")
        run_aggregator()
        
        logger.info("Waiting for the database for {} seconds ...".format(SAVE_DELAY_SECONDS))
        time.sleep(SAVE_DELAY_SECONDS)
        
        logger.info("Running price predictor ...")
        run_price_predictor()
        
        logger.info("Sleeping for {} seconds ...".format(INTERVAL_SECONDS))
        time.sleep(INTERVAL_SECONDS)


logger = get_logger()

if __name__ == "__main__":
    main()
