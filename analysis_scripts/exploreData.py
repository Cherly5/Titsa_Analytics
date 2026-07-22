import requests
from google.transit import gtfs_realtime_pb2
import pandas as pd
from datetime import datetime


# ------------------------------
# 1. URLs de los feeds GTFS-RT
# ------------------------------
URL_POSITION = "http://apps.titsa.com/gtfsfiles/GTFS-RT/position.bin"
URL_TRIPUPDATE = "http://apps.titsa.com/gtfsfiles/GTFS-RT/tripUpdate.bin"
URL_ALERT = "http://apps.titsa.com/gtfsfiles/GTFS-RT/alert.bin"


# ----------------------------------------------
# 2. Funciones auxiliares para descargar el feed
# ----------------------------------------------
def download_feed(url):
    response = requests.get(url)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed


def unix_to_ts(unix):
    if unix == 0 or unix is None:
        return None
    try:
        return datetime.fromtimestamp(unix)
    except:
        return None


# -------------------------------------
# 3. Procesar VehiclePositions
# -------------------------------------
def parse_vehicle_positions(feed):
    rows = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue

        v = entity.vehicle

        rows.append({
            "vehicle_id": v.vehicle.id if v.vehicle.id else None,
            "trip_id": v.trip.trip_id if v.trip.trip_id else None,
            "route_id": v.trip.route_id if v.trip.route_id else None,
            "latitude": v.position.latitude if v.HasField("position") else None,
            "longitude": v.position.longitude if v.HasField("position") else None,
            "bearing": v.position.bearing if v.HasField("position") else None,
            "speed": v.position.speed if v.HasField("position") else None,
            "timestamp": unix_to_ts(v.timestamp)
        })
    return pd.DataFrame(rows)


# -------------------------------------
# 4. Procesar TripUpdates
# -------------------------------------
def parse_trip_updates(feed):
    rows = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        tu = entity.trip_update
        trip_id = tu.trip.trip_id
        route_id = tu.trip.route_id

        for stu in tu.stop_time_update:
            rows.append({
                "trip_id": trip_id,
                "route_id": route_id,
                "stop_id": stu.stop_id,
                "stop_sequence": stu.stop_sequence,

                "arrival_time": unix_to_ts(stu.arrival.time) if stu.HasField("arrival") else None,
                "departure_time": unix_to_ts(stu.departure.time) if stu.HasField("departure") else None,
                "arrival_delay": stu.arrival.delay if stu.HasField("arrival") else None,
                "departure_delay": stu.departure.delay if stu.HasField("departure") else None,
            })

    return pd.DataFrame(rows)


# -------------------------------------
# 5. Procesar Alerts
# -------------------------------------
def parse_alerts(feed):
    rows = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue

        alert = entity.alert

        rows.append({
            "cause": alert.cause,
            "effect": alert.effect,
            "header_text": alert.header_text.translation[0].text if alert.header_text.translation else None,
            "description_text": alert.description_text.translation[0].text if alert.description_text.translation else None
        })

    return pd.DataFrame(rows)


# -------------------------------------
# 6. DESCARGAR Y PROCESAR LOS FEEDS
# -------------------------------------
print("Descargando feeds...")

feed_pos = download_feed(URL_POSITION)
feed_tu = download_feed(URL_TRIPUPDATE)
feed_alert = download_feed(URL_ALERT)

df_pos = parse_vehicle_positions(feed_pos)
df_tu = parse_trip_updates(feed_tu)
df_alert = parse_alerts(feed_alert)

print("Feeds descargados y procesados.")
print()


# -------------------------------------
# 7. EXPLORACIÓN DE LOS DATOS
# -------------------------------------
print("=== VehiclePositions ===")
print(df_pos.head(20))
print(df_pos.info())
print()

print("=== TripUpdates ===")
print(df_tu.head(20))
print(df_tu.info())
print()

print("=== Alerts ===")
print(df_alert.head(10))
print(df_alert.info())
print()


# -------------------------------------
# 8. MÓDULO DE CALIDAD DE DATOS
# -------------------------------------
print("\n============================")
print(" ANALISIS DE CALIDAD DE DATOS")
print("============================\n")

quality_report = {}

# 1. arrival == departure
if not df_tu.empty:
    df_tu["arrival_equals_departure"] = df_tu["arrival_time"] == df_tu["departure_time"]
    quality_report["arrival_equals_departure_all"] = df_tu["arrival_equals_departure"].all()

# 2. timestamps nulos o inválidos
invalid_timestamps = df_pos["timestamp"].isna().sum()
quality_report["vehicle_positions_invalid_timestamps"] = int(invalid_timestamps)

# 3. vehículos sin posición
missing_positions = df_pos["latitude"].isna().sum()
quality_report["vehicles_without_position"] = int(missing_positions)

# 4. trip_ids negativos o raros
negative_trips = (df_tu["trip_id"].astype(str).str.startswith("-")).sum()
quality_report["negative_trip_ids"] = int(negative_trips)

# 5. paradas sin tiempo asignado
missing_arrivals = df_tu["arrival_time"].isna().sum()
missing_departures = df_tu["departure_time"].isna().sum()

quality_report["missing_arrival_times"] = int(missing_arrivals)
quality_report["missing_departure_times"] = int(missing_departures)

# 6. alertas vacías
quality_report["alerts_count"] = len(df_alert)


# -------------------------------------
# 9. MOSTRAR REPORTE
# -------------------------------------
print("\n=== DATA QUALITY REPORT ===")
for k, v in quality_report.items():
    print(f"{k}: {v}")

print("\nAnálisis completado.")
