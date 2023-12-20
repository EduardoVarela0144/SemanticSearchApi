tripletsVectorMapping = {
    "properties": {
        "article_id": {
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
        }

    }
}
