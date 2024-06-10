tripletsMapping = {
    "properties": {
        "article_id": {
            "type": "text"
        },
        "pmc_id": {
            "type": "text"
        },
        "sentence_text": {
            "type": "text"
        },
        "sentence_text_vector": {
            "type": "dense_vector",
            "dims": 768,
            "index": True,
            "similarity": "l2_norm"
        },
        "triples": {
            "type": "nested",
            "properties": {
                "subject": {
                    "type": "text"
                },
                "relation": {
                    "type": "text"
                },
                "object": {
                    "type": "text"
                }
            }}

    }
}
