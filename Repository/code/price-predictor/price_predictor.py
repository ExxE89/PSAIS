import collections
import datetime
import logging
import os
import pprint

import elasticsearch
import elasticsearch.helpers
import ruamel.yaml as yaml

import custom_math


ANALYSIS_DAYS = 3
DOCUMENT_TYPE = "prediction"
INDEX_NAME = "predictions"
INSERT_CHUNK_SIZE = 2500
NYSE_TRADE_END_HOUR = 20
NYSE_UTC_OFFSET = datetime.timedelta(hours=-6)
TIMEOUT = 60


def clear_index(db):
    try:
        db.indices.delete(index=INDEX_NAME)
    except elasticsearch.exceptions.NotFoundError:
        pass


def get_aggregation_body(config, field):
    return {
        "size": 0,
        "aggs": {
            "by_time" : {
                "date_histogram" : {
                    "field" : "date",
                    "interval" : "{}m".format(config["aggregation_interval_minutes"]),
                },
                "aggs" : {
                    "avg_value" : {
                        "avg" : {
                            "field" : field
                        }
                    }
                }
            }
        }
    }


def get_aggregated_prices(db, config):
    logger.debug("Fetching aggregations ...")
    
    response = db.search(
        index="stock_data",
        doc_type="stock_price",
        body=get_aggregation_body(config, "price"),
    )
    
    for doc_group in response["aggregations"]["by_time"]["buckets"]:
        if not doc_group["avg_value"]["value"]:
            logger.info("Skipping empty value for {}".format(doc_group["key_as_string"]))
            continue
        
        aggregation = {
            "date": doc_group["key_as_string"],
            "value": doc_group["avg_value"]["value"],
        }
        
        yield aggregation


def get_aggregated_sentiments(db, config):
    logger.debug("Fetching aggregations ...")
    
    response = db.search(
        index="sentiments",
        doc_type="sentiment",
        body=get_aggregation_body(config, "sentiment_relation"),
    )
    
    for doc_group in response["aggregations"]["by_time"]["buckets"]:
        if not doc_group["avg_value"]["value"]:
            logger.info("Skipping empty value for {}".format(doc_group["key_as_string"]))
            continue
        
        aggregation = {
            "date": doc_group["key_as_string"],
            "value": doc_group["avg_value"]["value"],
        }
        
        yield aggregation


def get_config():
    config_file = os.getenv("PRICE_CONFIG", "config.yaml")
    config_file = os.path.abspath(config_file)

    logger.debug("Using config file at {}".format(config_file))

    with open(config_file) as fh:
        content = fh.read()

    config = yaml.load(content)
    return config


def get_database(host):
    logger.debug("Connecting to database ...")
    db = elasticsearch.Elasticsearch(host, timeout=TIMEOUT)
    db.ping()
    logger.debug("Database connection successful")
    return db


def get_logger():
    logger = logging.getLogger("psais.pricepredictor")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger


def get_merged_aggregations(prices, sentiments):
    merged = {}
    
    for price in prices:
        if price["date"] in merged:
            merged[price["date"]]["price"] = price["value"]
        else:
            merged[price["date"]] = {
                "price": price["value"],
            }
    
    for sentiment in sentiments:
        if sentiment["date"] in merged:
            merged[sentiment["date"]]["sentiment"] = sentiment["value"]
        else:
            merged[sentiment["date"]] = {
                "sentiment": sentiment["value"],
            }
    
    def merge_dict_item(item):
        date = get_parsed_elasticsearch_time(item[0])
        
        result = {
            "date": date,
        }
        
        result.update(item[1])
        return result
    
    complete_objects = merged.items()
    complete_objects = map(merge_dict_item, complete_objects)
    complete_objects = filter(lambda x: "price" in x and "sentiment" in x, complete_objects)
    complete_objects = sorted(complete_objects, key=lambda x: x["date"])
    
    return complete_objects


def get_parsed_elasticsearch_time(formatted_time):
    return datetime.datetime.strptime(formatted_time, "%Y-%m-%dT%H:%M:%S.%fZ")


def get_predicted_price(price, diff):
    if diff > 0.05:
        return price * 1.01
    elif diff < -0.05:
        return price * 0.99
    else:
        return price


def get_predictions(trading_days):
    prev_day_means = ()
    
    for day, trading_day in trading_days.items():
        prices = tuple(map(lambda x: x["price"], trading_day))
        sentiments = tuple(map(lambda x: x["sentiment"], trading_day))
        mean_day = custom_math.mean(sentiments)
        
        if not prev_day_means: # Special handling for first item.
            prev_day_means = (mean_day,)
            continue
        
        mean_prev_days = custom_math.mean(prev_day_means)
        
        prev_day_means = (mean_day,) + prev_day_means
        prev_day_means = prev_day_means[:ANALYSIS_DAYS]
        
        sentiment_diff = mean_day - mean_prev_days
        
        prices_mean = custom_math.mean(prices)
        predicted_price = get_predicted_price(prices_mean, sentiment_diff)
        
        yield {
            "day": day,
            "change": sentiment_diff,
            "price": prices_mean,
            "predicted_price": predicted_price,
        }


def get_save_action(document):
    action = {
        "_op_type": "index",
        "_index": INDEX_NAME,
        "_type": DOCUMENT_TYPE,
    }
    
    action.update(document)
    return action


def get_trading_day_buckets(aggregations):
    result = collections.OrderedDict()
    
    for aggregation in aggregations:
        day = aggregation["date"] + NYSE_UTC_OFFSET
        
        if day.hour >= NYSE_TRADE_END_HOUR:
            day = day + datetime.timedelta(days=1)
        
        day = day.date()
        
        items = result.setdefault(day, [])
        items.append(aggregation)
    
    return result


def save_predictions(db, predictions):
    documents = []
    
    for prediction in predictions:
        for hour in range(24):
            for minute in range(0, 60, 2):
                time = datetime.time(hour=hour, minute=minute)
                date = datetime.datetime.combine(prediction["day"], time)
                
                document = {
                    "date": date,
                }
                
                diff = prediction["predicted_price"] - prediction["price"]
                
                if diff > 0:
                    document["predicted_price_pos"] = prediction["predicted_price"]
                elif diff < 0:
                    document["predicted_price_neg"] = prediction["predicted_price"]
                
                documents.append(document)
    
    save_actions = map(get_save_action, documents)
    elasticsearch.helpers.bulk(db, save_actions, chunk_size=INSERT_CHUNK_SIZE)


def main():
    config = get_config()
    logger.setLevel(config["log_level"])
    db = get_database(config["database"]["host"])
    
    prices = get_aggregated_prices(db, config)
    sentiments = get_aggregated_sentiments(db, config)
    
    merged_aggregations = get_merged_aggregations(prices, sentiments)
    trading_days = get_trading_day_buckets(merged_aggregations)
    predictions = get_predictions(trading_days)
    
    predictions = filter(lambda x: x["price"] != x["predicted_price"], predictions)
    predictions = tuple(predictions)
    #pp.pprint(predictions)
    
    logger.info("Deleting index {} ...".format(INDEX_NAME))
    clear_index(db)
    
    logger.info("Saving {} predictions ...".format(len(predictions)))
    save_predictions(db, predictions)
    


logger = get_logger()
pp = pprint.PrettyPrinter(indent=4)

if __name__ == "__main__":
    main()
