articleMapping = {
    "properties": {
        "title": {
            "type": "text"
        },
        "authors": {
            "type": "keyword",
            "ignore_above": 256
        },
        "journal": {
            "type": "text"
        },
        "abstract": {
            "type": "text"
        },
        "doi": {
            "type": "text"
        },
        "issn": {
            "type": "text"
        },
        "year": {
            "type": "text"
        },
        "volume": {
            "type": "text"
        },
        "issue": {
            "type": "text"
        },
        "pages": {
            "type": "text"
        },
        "url": {
            "type": "text"
        },
        "pmc_id": {
            "type": "text",
            "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
            }, },
        "content": {
            "type": "text"
        },
        "path": {
            "type": "text"
        },
        "vector": {
            "type": "dense_vector",
            "dims": 768,
            "index": True,
            "similarity": "l2_norm"
        }

    }
}
