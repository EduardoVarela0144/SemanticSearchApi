from stanza.server import CoreNLPClient

sentences = [
    "The doctor read the file",
    "The patient is sick",
    "The patient was given a prescription",
]

with CoreNLPClient(annotators=["openie"], be_quiet=False, ) as client:
    for text in sentences:
        ann = client.annotate(text)
        #print(ann)
        for sentence in ann.sentence:
            for triple in sentence.openieTriple:
                print("Subject:", triple.subject)
                print("Relation:", triple.relation)
                print("Object:", triple.object)