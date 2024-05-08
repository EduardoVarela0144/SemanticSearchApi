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
        padded_triplets = triplets_data + \
            [0] * (self.max_triplets_length - len(triplets_data))
        return {'id': self.data[idx]['id'], 'article_id': self.data[idx]['article_id'], 'sentence_text': self.data[idx]['sentence_text'], 'triplets': padded_triplets}


class TripletDataLoader:
    def __init__(self, es):
        self.es = Elasticsearch(es)

    def my_collate(self, batch, options=None):
        if options is None:
            options = {'sentence': ['sentence_text'], 'subject': ['triplets'], 'relation': ['triplets'], 'object': ['triplets']}

        if isinstance(batch[0], dict):
            data = {'sentence': [], 'subject': [], 'relation': [], 'object': [], 'lengths': []}
            for item in batch:
                for key, value in options.items():
                    if '+' in key:
                        concatenated_key = key.replace('+', '_and_')
                        concatenated_value = '+'.join([item[val] for val in value])
                        data[concatenated_key].append(concatenated_value)
                    else:
                        data[key].append(item[value[0]])
                data['lengths'].append(len(item['triplets']))
            return data

        else:
            return batch

    def get_triplets_data_set(self, page_number, page_size, max_triplets_length, options=None):
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
                sentence_text = result.get('sentence_text', '')
                triplets_data = result.get('triplets', [])

                result_collection.append({
                    'id': triplet_id,
                    'article_id': article_id,
                    'sentence_text': sentence_text,
                    'triplets': triplets_data,
                })

            dataset = TripletsDataset(
                result_collection[start_index:start_index+page_size], max_triplets_length)

            dataloader = DataLoader(
                dataset, batch_size=page_size, shuffle=True)

            dataloader = DataLoader(
                dataset, batch_size=page_size, collate_fn=lambda batch: self.my_collate(batch, options=options))

            return dataloader

        except NotFoundError:
            return jsonify({'error': 'No articles found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'})


class TripletsDataset(Dataset):
    def __init__(self, data, max_triplets_length):
        self.data = data
        self.max_triplets_length = max_triplets_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        # No rellenar con ceros aquí, devolver la longitud real de los tripletes
        triplets_data = self.data[idx]['triplets']
        return {
            'id': self.data[idx]['id'],
            'article_id': self.data[idx]['article_id'],
            'sentence_text': self.data[idx]['sentence_text'],
            'triplets': triplets_data,
            'length': len(triplets_data)  # Agregar la longitud de los tripletes
        }




def main():
    # Crear una instancia de TripletDataLoader
    loader = TripletDataLoader("http://localhost:9200")

    # Definir opciones para el cargador de datos
    options = {'sentence': ['sentence_text'], 'subject': [
        'triplets'], 'relation': ['triplets'], 'object': ['triplets']}

    # Obtener el DataLoader para la página 1 con tamaño de página 10 y longitud máxima de triplets 50
    dataloader = loader.get_triplets_data_set(1, 10, 50, options=options)

    # Iterar sobre el DataLoader y mostrar los datos de cada lote
    for i, batch in enumerate(dataloader):
        if i == 0:  # Solo imprimir el primer lote
            print(batch)
            break


if __name__ == "__main__":
    main()
