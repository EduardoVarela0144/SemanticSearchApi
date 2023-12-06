articleMapping = {
    "properties": {
        "title": {
            "type": "text"
        },
        "authors": {
            "type": "text"
        },
        "journal": {
            "type": "text"
        },
        "issn": {
            "type": "text"
        },
        "doi": {
            "type": "text"
        },
        "pmc_id": {
            "type": "text"
        },
        "keys": {
            "type": "text"
        },
        "abstract": {
            "type": "text"
        },
        "objectives": {
            "type": "text"
        },
        "methods": {
            "type": "text"
        },
        "content": {
            "type": "text"
        },
        "results": {
            "type": "text"
        },
        "conclusion": {
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
