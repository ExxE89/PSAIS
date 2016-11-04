import csv
import logging
import os

import elasticsearch
import ruamel.yaml as yaml


CONTEXT_TIMEOUT = "1m"
SCROLL_BATCH_SIZE = 5000


def get_documents(db, dump_task):
    logger.info("Initializing scroll search ...")
    
    response = db.search(
        index=dump_task["index"],
        doc_type=dump_task["doc_type"],
        scroll=CONTEXT_TIMEOUT,
        search_type="scan",
        body={
            "query": {
                "constant_score": {
                    "filter": dump_task["search_filter"],
                },
            },
            "size": SCROLL_BATCH_SIZE,
        },
    )
    
    scroll_id = response["_scroll_id"]
    cur_count = response["hits"]["total"]
    
    logger.info("Streaming {} documents ...".format(cur_count))
    fetched_count = 0
    processed_count = 0
    
    while cur_count > 0:
        response = db.scroll(scroll_id=scroll_id, scroll=CONTEXT_TIMEOUT)
        cur_count = len(response["hits"]["hits"])
        scroll_id = response["_scroll_id"]
        
        fetched_count += cur_count
        progress = fetched_count / response["hits"]["total"] * 100
        remaining = response["hits"]["total"] - fetched_count
        
        logger.info("{}/{} documents ({:.1f} %) fetched, {} remaining ...".format(
            fetched_count,
            response["hits"]["total"],
            progress,
            remaining,
        ))
        
        if response["hits"]["hits"]:
            logger.debug("Time range: From ...")
            logger.debug("{} to".format(response["hits"]["hits"][0]["_source"]["date"]))
            logger.debug("{}".format(response["hits"]["hits"][-1]["_source"]["date"]))
        
        for hit in response["hits"]["hits"]:
            document = {}
            hit["_source"]["id"] = hit["_id"]
            
            try:
                for fieldname in dump_task["fieldnames"]:
                    document[fieldname] = hit["_source"][fieldname]
            except KeyError:
                logger.debug("Skipping document")
                continue
            
            yield document
            
            processed_count += 1
            
            if processed_count >= dump_task["max_documents"]:
                logger.debug("Reached max document count ({}), finishing.".format(processed_count))
                return


def get_config():
    config_file = os.getenv("DUMPER_CONFIG", "config.yaml")
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
    logger = logging.getLogger("psais.dumper.csv")
    logger.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    
    logger.addHandler(ch)
    
    return logger


def save_to_csv(documents, fieldnames, destination):
    with open(destination, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        
        for document in documents:
            writer.writerow(document)


def main():
    config = get_config()
    logger.setLevel(config["log_level"])
    db = get_database(config["database"]["host"])
    
    for dump_task in config["dump_tasks"]:
        documents = get_documents(db, dump_task)
        documents = sorted(documents, key=lambda x: x["date"])
        save_to_csv(documents, dump_task["fieldnames"], dump_task["destination"])


logger = get_logger()

if __name__ == "__main__":
    main()
