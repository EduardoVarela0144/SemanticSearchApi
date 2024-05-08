import torch
from torch.utils.data import Dataset, DataLoader
from elasticsearch import Elasticsearch, NotFoundError
from flask import jsonify
import os

class TripletsDataset(Dataset):
    def __init__(self, data, max_triplets_length):
        self.data = data
        self.max_triplets_length = max_triplets_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        # Pad triplets to max_triplets_length
        triplets_data = self.data[idx]['triplets']
        padded_triplets = triplets_data + [0] * (self.max_triplets_length - len(triplets_data))
        return {'id': self.data[idx]['id'], 'article_id': self.data[idx]['article_id'], 'triplets': padded_triplets}

class TripletDataLoader:
    def __init__(self, es):
        self.es = Elasticsearch(es)
    
    def my_collate(self, batch):
        if isinstance(batch[0], tuple):
            data = [item[0] for item in batch]
            target = [item[1] for item in batch]
        else:
            data = batch
            target = None
        target = torch.LongTensor(target) if target is not None else None
        return [data, target]
    
    def get_triplets_data_set(self, page_number, page_size, max_triplets_length):
        try:
            index_name = 'triplets'
            page_number = int(page_number)
            page_size = int(page_size)
            start_index = (page_number - 1) * page_size

            response = self.es.search(index=index_name, body={
                                      'query': {'match_all': {}}})
            triplets = response.get('hits', {}).get('hits', [])

            if not triplets:
                return jsonify({'error': 'No triplets found in Elasticsearch'})

            result_collection = []
            for triplet in triplets:
                result = triplet.get('_source', {})
                triplet_id = triplet.get('_id', '')
                article_id = result.get('article_id', '')
                triplets_data = result.get('triplets', [])

                result_collection.append({
                    'id': triplet_id,
                    'article_id': article_id,
                    'triplets': triplets_data,
                })

         

            dataset = TripletsDataset(
                result_collection[start_index:start_index+page_size], max_triplets_length)

            dataloader = DataLoader(
                dataset, batch_size=page_size, shuffle=True)
            
            dataloader = DataLoader(dataset, batch_size=page_size, collate_fn=self.my_collate)

            return dataloader

        except NotFoundError:
            return jsonify({'error': 'No articles found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'})

def main():
    # Crear una instancia de TripletDataLoader
    loader = TripletDataLoader("http://localhost:9200")

    # Obtener el DataLoader para la página 1 con tamaño de página 10 y longitud máxima de triplets 50
    dataloader = loader.get_triplets_data_set(1, 10, 50)

    # Iterar sobre el DataLoader y mostrar los datos de cada lote
    for batch in dataloader:
        print(batch)

if __name__ == "__main__":
    main()
