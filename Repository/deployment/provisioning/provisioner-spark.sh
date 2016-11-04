#!/bin/bash

set -x

function install_elasticsearch_hadoop_connector() {
    wget -q --directory-prefix=/tmp http://download.elastic.co/hadoop/elasticsearch-hadoop-2.2.0.zip
    unzip -q -d /opt /tmp/elasticsearch-hadoop-2.2.0.zip
    mv /opt/elasticsearch-hadoop-2.2.0 /opt/elasticsearch-hadoop
}

function install_spark() {
    wget -q -O - http://d3kbcqa49mib13.cloudfront.net/spark-1.6.1-bin-hadoop2.6.tgz | tar -xz --directory /opt
    mv /opt/spark-1.6.1-bin-hadoop2.6 /opt/spark
}

function install_spark_slaves() {
    # Clear the file.
    > /opt/spark/conf/slaves
    
    echo "141.7.63.156" >> /opt/spark/conf/slaves
    echo "141.7.63.161" >> /opt/spark/conf/slaves
}

function main() {
    install_spark
    install_spark_slaves
    install_elasticsearch_hadoop_connector
}

main
