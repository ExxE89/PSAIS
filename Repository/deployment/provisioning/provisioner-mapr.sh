#!/bin/bash

set -x

function install_elasticsearch-hadoop-connector() {
	mkdir /opt/mapr/spark/es-hadoop-connector
	wget -q --directory-prefix=/opt/mapr/spark/es-hadoop-connector http://download.elastic.co/hadoop/elasticsearch-hadoop-2.2.0.zip
	unzip -q -d /opt/mapr/spark/es-hadoop-connector/ /opt/mapr/spark/es-hadoop-connector/elasticsearch-hadoop-2.2.0.zip
}

function install_mapr() {
    wget -q -O - https://package.mapr.com/releases/installer/mapr-setup.sh | bash -s -- --yes
}

function main() {
    install_mapr
    install_elasticsearch-hadoop-connector
}

main
