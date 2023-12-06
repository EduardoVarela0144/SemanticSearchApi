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
                "triplets": {
                    "type": "nested",
                    "properties": {
                        "subject": {
                            "type": "nested",
                            "properties": {
                                "text": {
                                    "type": "text"
                                },
                                "vector": {
                                    "type": "dense_vector",
                                    "dims": 768,
                                    "index": True,
                                    "similarity": "l2_norm"
                                }
                            }
                        },
                        "relation": {
                            "type": "nested",
                            "properties": {
                                "text": {
                                    "type": "text"
                                },
                                "vector": {
                                    "type": "dense_vector",
                                    "dims": 768,
                                    "index": True,
                                    "similarity": "l2_norm"
                                }
                            }
                        },
                        "object": {
                            "type": "nested",
                            "properties": {
                                "text": {
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
                    }
                }
            }
        }
    }
}
