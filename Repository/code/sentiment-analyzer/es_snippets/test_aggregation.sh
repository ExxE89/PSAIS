curl -XGET 'localhost:9200/twitter/tweet/_search?pretty' -d '{
    "aggs": {
        "by_time" : {
            "date_histogram" : {
                "field" : "date",
                "interval" : "10000s"
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
}'
