import requests
import gtfs_realtime_pb2
import time
from datetime import datetime
import sys

def check_update_rate(feed_url):
    print(f"Iniciando comprobación de la frecuencia de actualización para: {feed_url}")
    print("Presiona Ctrl+C para detener.\n")

    last_timestamp = None
    last_update_time = None

    try:
        while True:
            try:
                response = requests.get(feed_url, timeout=10)
                if response.status_code == 200:
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(response.content)
                    current_timestamp = feed.header.timestamp

                    if current_timestamp != last_timestamp:
                        now = datetime.now()

                        if last_timestamp is not None:
                            diff_seconds = current_timestamp - last_timestamp
                            time_since_last_seen = (now - last_update_time).total_seconds()

                            print(f"[{now.strftime('%H:%M:%S')}] Datos actualizados")
                            print(f"  => Tiempo de diferencia según el feed: {diff_seconds}")
                            print(f"  => Tiempo transcurrido en capturar los datos: {time_since_last_seen:.1f}")
                        else:
                            print(f"[{now.strftime('%H:%M:%S')}] Dato inicial capturado. Esperando al próximo cambio...")

                        last_timestamp = current_timestamp
                        last_update_time = now
                else:
                    print(f"Error al descargar: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Error de conexión: {e} - Reintentando en el próximo ciclo...")

            time.sleep(5)

    except KeyboardInterrupt:
        print("\nComprobación detenida.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python check_update_rate.py <URL_del_feed>")
        sys.exit(1)
    check_update_rate(sys.argv[1])
