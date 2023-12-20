tripletsMapping = {
    "properties": {
        "article_id": {
            "type": "text"
        },
        "article_title": {
            "type": "text"
        },
        "data_analysis": {
            "type": "nested",
            "properties": {
                "sentence_text": {
                    "type": "text"
                },
                "sentence_text_vector": {

                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "l2_norm"

                },
                "triplets": {
                    "type": "nested",
                    "properties": {
                        "subject": {
                            "type": "nested",
                            "properties": {
                                "text": {
                                    "type": "text"
                                }
                            }
                        },
                        "relation": {
                            "type": "nested",
                            "properties": {
                                "text": {
                                    "type": "text"
                                }
                            }
                        },
                        "object": {
                            "type": "nested",
                            "properties": {
                                "text": {
                                    "type": "text"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
