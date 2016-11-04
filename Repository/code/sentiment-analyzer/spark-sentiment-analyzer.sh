#!/bin/bash

set -x

function run_sentiment_analyzer() {
	export PYSPARK_PYTHON=python3.4
    
    if [ -z "${SENTIMENT_CONFIG}" ]; then
    	export SENTIMENT_CONFIG=/etc/psais/sentiment-analyzer-spark.yaml
    fi
	
	/opt/spark/bin/spark-submit \
		--deploy-mode client \
		--jars /opt/elasticsearch-hadoop/dist/elasticsearch-hadoop-2.2.0.jar \
		/opt/psais/sentiment-analyzer/sentiment_analyzer_spark.py
}

function main() {
	run_sentiment_analyzer
}

main
