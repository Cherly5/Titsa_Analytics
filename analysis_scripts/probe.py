import requests
from google.transit import gtfs_realtime_pb2
import pandas as pd
from datetime import datetime

# URLs de TITSA
URL_POSITION = "http://apps.titsa.com/gtfsfiles/GTFS-RT/position.bin"
URL_TRIPUPDATE = "http://apps.titsa.com/gtfsfiles/GTFS-RT/tripUpdate.bin"
URL_ALERT = "http://apps.titsa.com/gtfsfiles/GTFS-RT/alert.bin"

def descargar_y_parsear(url):
    response = requests.get(url)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed

# Descargar feeds
feed_pos = descargar_y_parsear(URL_POSITION)
feed_trip = descargar_y_parsear(URL_TRIPUPDATE)
feed_alert = descargar_y_parsear(URL_ALERT)

# ------------ VEHICLE POSITIONS ------------------
vehicle_data = []
for entity in feed_pos.entity:
    if entity.HasField("vehicle"):
        v = entity.vehicle
        vehicle_data.append({
            "trip_id": v.trip.trip_id,
            "route_id": v.trip.route_id,
            "vehicle_id": v.vehicle.id,
            "latitude": v.position.latitude,
            "longitude": v.position.longitude,
            "bearing": getattr(v.position, "bearing", None),
            "speed": getattr(v.position, "speed", None),
            "timestamp": datetime.fromtimestamp(v.timestamp)
        })

df_positions = pd.DataFrame(vehicle_data)
print("\n=== VEHICLE POSITIONS ===")
print(df_positions.head())

# ------------ TRIP UPDATES ------------------
trip_data = []
for entity in feed_trip.entity:
    if entity.HasField("trip_update"):
        t = entity.trip_update
        for stu in t.stop_time_update:
            trip_data.append({
                "trip_id": t.trip.trip_id,
                "route_id": t.trip.route_id,
                "stop_id": stu.stop_id,
                "arrival": getattr(stu.arrival, "time", None),
                "departure": getattr(stu.departure, "time", None),
                "delay": getattr(stu.arrival, "delay", None)
            })

df_trip = pd.DataFrame(trip_data)
print("\n=== TRIP UPDATES ===")
print(df_trip.head())

# ------------ ALERTS ------------------
alert_data = []
for entity in feed_alert.entity:
    if entity.HasField("alert"):
        a = entity.alert
        alert_data.append({
            "header": a.header_text.translation[0].text if a.header_text.translation else None,
            "description": a.description_text.translation[0].text if a.description_text.translation else None,
            "cause": a.cause,
            "effect": a.effect
        })

df_alerts = pd.DataFrame(alert_data)
print("\n=== ALERTS ===")
print(df_alerts.head())
