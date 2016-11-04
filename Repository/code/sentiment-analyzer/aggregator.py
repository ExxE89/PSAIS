import logging
import os

import elasticsearch
import elasticsearch.helpers
import ruamel.yaml as yaml


DOCUMENT_TYPE = "sentiment"
INDEX_NAME = "sentiments"
INSERT_CHUNK_SIZE = 2500
TIMEOUT = 60


def clear_index(db):
    try:
        db.indices.delete(index=INDEX_NAME)
    except elasticsearch.exceptions.NotFoundError:
        pass


def get_aggregation_body(config):
    return {
        "size": 0,
        "aggs": {
            "by_time" : {
                "date_histogram" : {
                    "field" : "date",
                    "interval" : "{}m".format(config["aggregation"]["time_interval_minutes"]),
                },
                "aggs": {
                    "by_sentiment" : {
                        "terms" : {
                            "script" : {
                                "lang": "groovy",
                                "file": "polarity_to_class",
                                "params": {
                                    "classifier": "naive_bayes"
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def get_aggregated_documents(db, config):
    logger.info("Sending aggregation request and waiting for results ...")
    
    response = db.search(
        index="twitter",
        doc_type="tweet",
        body=get_aggregation_body(config),
    )
    
    logger.info("Parsing results ...")
    
    for doc_group in response["aggregations"]["by_time"]["buckets"]:
        aggregation = {
            "date": doc_group["key_as_string"],
        }
        
        for sentiment in doc_group["by_sentiment"]["buckets"]:
            aggregation[sentiment["key"]] = sentiment["doc_count"]
        
        if "pos" in aggregation and "neg" in aggregation:
            aggregation["sentiment_relation"] = aggregation["pos"] / (aggregation["pos"] + aggregation["neg"])
        
        yield aggregation


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
    db = elasticsearch.Elasticsearch(host, timeout=TIMEOUT)
    db.ping()
    logger.debug("Database connection successful")
    return db


def get_logger():
    logger = logging.getLogger("psais.sentiment.aggregator")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger


def get_save_action(document):
    action = {
        "_op_type": "index",
        "_index": INDEX_NAME,
        "_type": DOCUMENT_TYPE,
    }
    
    action.update(document)
    return action


def save_aggregations(db, aggregations):
    save_actions = map(get_save_action, aggregations)
    elasticsearch.helpers.bulk(db, save_actions, chunk_size=INSERT_CHUNK_SIZE)


def main():
    config = get_config()
    logger.setLevel(config["log_level"])
    db = get_database(config["database"]["host"])
    
    aggregations = get_aggregated_documents(db, config)
    aggregations = tuple(aggregations)
    
    logger.info("Deleting index {} ...".format(INDEX_NAME))
    clear_index(db)
    
    logger.info("Saving {} aggregated values ...".format(len(aggregations)))
    save_aggregations(db, aggregations)


logger = get_logger()

if __name__ == "__main__":
    main()
