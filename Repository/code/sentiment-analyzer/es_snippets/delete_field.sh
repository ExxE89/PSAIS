curl -XPOST 'localhost:9200/twitter/tweet/_update_by_query?pretty' -d '{
    "script" : {
        "lang": "groovy",
        "file": "delete_field",
        "params": {
            "field": "sentiment"
        }
    }
}'
