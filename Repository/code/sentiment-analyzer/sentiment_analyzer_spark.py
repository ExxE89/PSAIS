import json
import os
import tempfile
import zipfile

from pyspark import SparkContext, SparkConf

import classifiers
import sentiment_analyzer as sa

SENTIMENT_ANALYZER_HOME = "/opt/psais/sentiment-analyzer"
CLASSIFIERS_BASE_DIR = os.path.join(SENTIMENT_ANALYZER_HOME, "classifiers")
NAIVE_BAYES_BASE_DIR = os.path.join(CLASSIFIERS_BASE_DIR, "naive_bayes")
NAIVE_BAYES_CORPUS_BASE_DIR = os.path.join(NAIVE_BAYES_BASE_DIR, "corpus")


def add_spark_files(sc):
    classifiers_archive = create_classifier_zipfile()
    
    sc.addPyFile(classifiers_archive)
    sc.addPyFile(os.path.join(SENTIMENT_ANALYZER_HOME, "sentiment_analyzer.py"))
    sc.addFile(os.path.join(NAIVE_BAYES_BASE_DIR, "naive_bayes.pickle.xz"))
    sc.addFile(os.path.join(NAIVE_BAYES_BASE_DIR, "stop_words.txt"))
    sc.addFile(os.path.join(NAIVE_BAYES_CORPUS_BASE_DIR, "negative.txt"))
    sc.addFile(os.path.join(NAIVE_BAYES_CORPUS_BASE_DIR, "neutral.txt"))
    sc.addFile(os.path.join(NAIVE_BAYES_CORPUS_BASE_DIR, "positive.txt"))


def create_classifier_zipfile():
    tempdir = tempfile.mkdtemp()
    zip_path = os.path.join(tempdir, "sentiment-classifiers.zip")
    basename = os.path.basename(CLASSIFIERS_BASE_DIR)
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as fh:
        for root, dirs, files in os.walk(CLASSIFIERS_BASE_DIR):
            for file in files:
                fullpath = os.path.join(root, file)
                
                relpath = os.path.relpath(fullpath, CLASSIFIERS_BASE_DIR)
                relpath = os.path.join(basename, relpath)
                
                fh.write(fullpath, relpath)
    
    return zip_path


def get_es_conf():
    query = {
        "query": config["search_filter"],
    }

    es_conf = {
        "es.resource": sa.INDEX_NAME + "/" + sa.DOCUMENT_TYPE ,
        "es.nodes": config["database"]["host"].split(":")[0],
        "es.query": json.dumps(query),
    }
    
    return es_conf


def get_save_action(tweet):
    return {
        "_op_type": "update",
        "_id": tweet.id,
        "_index": sa.INDEX_NAME,
        "_type": sa.DOCUMENT_TYPE,
        "doc": tweet.data,
    }


def get_spark_context():
    spark_conf = SparkConf()
    spark_conf.setAppName("SentimentAnalyzerSpark")
    spark_conf.setMaster(config["spark_master"])

    sc = SparkContext(conf=spark_conf)
    add_spark_files(sc)
    
    return sc


def run_analysis(sc, classifier, es_conf):
    rdd = sc.newAPIHadoopRDD(
        inputFormatClass="org.elasticsearch.hadoop.mr.EsInputFormat",
        keyClass="org.apache.hadoop.io.NullWritable",
        valueClass="org.elasticsearch.hadoop.mr.LinkedMapWritable",
        conf=es_conf,
    )

    rdd = rdd.map(tweet_document_named_tuple)
    rdd = rdd.filter(lambda x: not sa.is_spam_tweet(x))
    rdd = rdd.map(sa.get_url_filtered_tweet)
    rdd = rdd.map(lambda x: sa.get_classified_tweet(classifier, config["classifier"], x))
    rdd = rdd.map(get_save_action)
    
    db = sa.get_database(config["database"]["host"])

    sa.elasticsearch.helpers.bulk(
        db,
        rdd.toLocalIterator(),
        chunk_size=sa.UPDATE_CHUNK_SIZE,
    )


def tweet_document_named_tuple(x):
    return sa.TweetDocument(id=x[0], data=x[1])


def main():
    sa.load_spam_filters()

    sc = get_spark_context()
    classifier = getattr(classifiers, config["classifier"]).classify
    es_conf = get_es_conf()
    
    run_analysis(sc, classifier, es_conf)
    
    sc.stop()


config = sa.get_config()


if __name__ == "__main__":
    main()
