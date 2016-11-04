#!/bin/bash

set -x

function get_my_ip_address() {
    # Source: http://stackoverflow.com/q/19224811
    echo $(ip addr | awk '/inet/ && /eth1/{sub(/\/.*$/,"",$2); print $2}')
}

function install_default_software() {
    apt-get update
    apt-get install --yes git htop ntp openjdk-7-jdk python3 python3-dev unzip zip
}

function install_elasticsearch() {
    # Source: https://www.elastic.co/guide/en/elasticsearch/reference/current/setup-repositories.html

    wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | apt-key add -
    echo "deb http://packages.elastic.co/elasticsearch/2.x/debian stable main" | tee -a /etc/apt/sources.list.d/elasticsearch-2.x.list

    apt-get update
    apt-get install --yes elasticsearch

    echo "path.scripts: /opt/psais/sentiment-analyzer/es_scripts" >> /etc/elasticsearch/elasticsearch.yml

    service elasticsearch start
}

function install_grafana() {
    wget -q -O - https://grafanarel.s3.amazonaws.com/builds/grafana-3.0.4-1464167696.linux-x64.tar.gz | tar -xz --directory /opt
    mv /opt/grafana-3.0.4-1464167696 /opt/grafana
    
    mkdir -p /opt/grafana/data
    cp /provisioning/grafana.db /opt/grafana/data
}

function install_kibana() {
    wget -q -O - https://download.elastic.co/kibana/kibana/kibana-4.5.1-linux-x64.tar.gz | tar -xz --directory /opt
    mv /opt/kibana-4.5.1-linux-x64 /opt/kibana
    git clone https://github.com/sbeyn/kibana-plugin-line-sg /opt/kibana/installedPlugins/line-sg
}

function install_psais_dependencies() {
    wget -q -O - https://bootstrap.pypa.io/get-pip.py | python3

    pip install -r /opt/psais/sentiment-analyzer/requirements.txt
    pip install -r /opt/psais/twitter-scraper/requirements.txt
    pip install -r /opt/psais/yahoo-finance-scraper/requirements.txt

    install_elasticsearch
    install_kibana
    install_grafana
}

function install_psais_services() {
    cp /provisioning/upstart/*.conf /etc/init
    
    # Make services available for tab completion when using "service <service name> [...]" command.
    ls /provisioning/upstart/*.conf | xargs -n1 basename | cut -d. -f1 | \
        awk '{OFS=""} {print "/etc/init.d/", $0}' | xargs -n1 touch
}

function install_ssh_keys() {
    mkdir -p /root/.ssh

    ssh-keygen -f /provisioning/private_key -y >> /root/.ssh/authorized_keys
    cp /provisioning/private_key /root/.ssh/id_rsa

    chmod 0700 /root/.ssh
    chmod 0600 /root/.ssh/*
}

function replace_default_route() {
	ip route replace default via $(get_my_ip_address)
}

function set_timezone() {
    timedatectl set-timezone Europe/Berlin
}

function setup_hostname() {
    hostname $(cat /etc/hostname)

    cp /etc/hosts /etc/hosts.bak

    cat > /etc/hosts <<EOT
127.0.0.1   localhost vagrant.vm vagrant
$(get_my_ip_address)   $(hostname)

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOT
}

function main() {
    set_timezone
    setup_hostname
    replace_default_route
    install_ssh_keys
    install_psais_services
    install_default_software
    install_psais_dependencies
}

main
