import logging
import requests
import json
from google.protobuf.json_format import MessageToDict
import gtfs_realtime_pb2
import sys

def fetch_and_parse_feed(url):
    """Descarga y parsea un feed GTFS Realtime desde una URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed
    except requests.exceptions.RequestException as e:
        print(f"Error al descargar el feed: {e}")
        raise
    except Exception as e:
        print(f"Error al parsear el feed: {e}")
        raise

def save_feed_as_json(feed_dict, output_file):
    """Guarda el diccionario del feed como un archivo JSON."""
    file = None
    try:
        file = open(output_file, 'w', encoding='utf-8')
        json.dump(feed_dict, file, indent=2, ensure_ascii=False)
        return True
    except (IOError, OSError) as e:
        logging.error(f"Error de archivo: {e}")
        return False
    except TypeError as e:
        logging.error(f"Datos no serializables: {e}")
        return False
    finally:
        if file is not None:
            file.close()

def main(feed_url, output_json_path):
    print(f"Descargando feed desde: {feed_url}")
    feed = fetch_and_parse_feed(feed_url)
    print(f"Feed descargado. Versión: {feed.header.gtfs_realtime_version}")
    print(f"Número de entidades: {len(feed.entity)}")

    feed_dict = MessageToDict(feed, preserving_proto_field_name=True)
    save_feed_as_json(feed_dict, output_json_path)
    print(f"JSON guardado en: {output_json_path}")

    entity_types = set()
    for entity in feed.entity:
        if entity.HasField('trip_update'):
            entity_types.add('trip_update')
        if entity.HasField('vehicle'):
            entity_types.add('vehicle')
        if entity.HasField('alert'):
            entity_types.add('alert')
    print(f"Tipos de entidades encontradas: {entity_types}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python feedScript.py <URL_del_feed> <salida_script.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])