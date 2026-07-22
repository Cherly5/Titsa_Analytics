import json
import os
import signal
import time
from collections import deque
from threading import Event

import requests
from dotenv import load_dotenv
from google.cloud import pubsub_v1

from analysis_scripts import gtfs_realtime_pb2
from utils import build_position_event_payload, build_trip_update_event_payload, build_alert_event_payload

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "tfg-movilidad-titsa")

TOPICS = {
    "vehicle": os.getenv("TOPIC_VEHICLES", "titsa-vehicle-positions"),
    "trip": os.getenv("TOPIC_TRIPS", "titsa-trip-updates"),
    "alert": os.getenv("TOPIC_ALERTS", "titsa-alerts")
}

URLS = {
    "vehicle": os.getenv("URL_VEHICLES"),
    "trip": os.getenv("URL_TRIPS"),
    "alert": os.getenv("URL_ALERTS")
}

POLL_INTERVALS = {
    "vehicle": int(os.getenv("POLL_INTERVAL_VEHICLES", 30)),
    "trip": int(os.getenv("POLL_INTERVAL_TRIPS", 30)),
    "alert": int(os.getenv("POLL_INTERVAL_ALERTS", 300))
}

publisher = pubsub_v1.PublisherClient()

topic_paths = {}
for key, value in TOPICS.items():
    topic_paths[key] = publisher.topic_path(PROJECT_ID, value)

seen_vehicle_events = deque(maxlen=5000)
seen_trip_events = deque(maxlen=5000)
seen_alert_events = deque(maxlen=5000)

running = True
shutdown_event = Event()

def signal_handler(sig, frame):
    global running
    print("\nSeñal de interrupción recibida. Cerrando productor...")
    running = False
    shutdown_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def publish_event(topic_path, event):
    publisher.publish(
        topic_path,
        json.dumps(event).encode("utf-8")
    )


def ingest_vehicle_positions():
    try:
        response = requests.get(URLS["vehicle"], timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error de red al capturar vehículos: {e}")
        return

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    published_this_poll = 0

    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue

        vehicle = entity.vehicle
        key = (vehicle.vehicle.id, vehicle.timestamp)
        if key in seen_vehicle_events:
            continue

        seen_vehicle_events.append(key)
        event = build_position_event_payload(vehicle)
        publish_event(topic_paths["vehicle"], event)
        published_this_poll += 1

    print(f"Vehicle poll → {published_this_poll} NEW Events published")


def ingest_trip_updates():
    try:
        response = requests.get(URLS["trip"], timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error de red al capturar trip updates: {e}")
        return

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    published_this_poll = 0

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        trip_update = entity.trip_update

        for stop_time_update in trip_update.stop_time_update:
            event_time = None
            if stop_time_update.HasField("arrival"):
                event_time = stop_time_update.arrival.time
            elif stop_time_update.HasField("departure"):
                event_time = stop_time_update.departure.time

            if event_time is None:
                continue

            key = (trip_update.trip.trip_id, stop_time_update.stop_id, event_time)
            if key in seen_trip_events:
                continue

            seen_trip_events.append(key)
            event = build_trip_update_event_payload(trip_update, stop_time_update, event_time)
            publish_event(topic_paths["trip"], event)
            published_this_poll += 1

    print(f"Trip poll → {published_this_poll} NEW Events published")


def ingest_alerts():
    try:
        response = requests.get(URLS["alert"], timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error de red al capturar alertas: {e}")
        return

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    published_this_poll = 0

    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue

        alert = entity.alert
        key = (alert.cause, alert.effect)
        if key in seen_alert_events:
            continue

        seen_alert_events.append(key)
        event = build_alert_event_payload(alert)
        publish_event(topic_paths["alert"], event)
        published_this_poll += 1

    print(f"Alert poll → {published_this_poll} Events published")


last_run = {
    "vehicle": 0,
    "trip": 0,
    "alert": 0
}

print("Capturador continuo iniciado... (Ctrl+C para detener)")

while running:
    now = time.time()

    if now - last_run["vehicle"] >= POLL_INTERVALS["vehicle"]:
        ingest_vehicle_positions()
        last_run["vehicle"] = now

    if now - last_run["trip"] >= POLL_INTERVALS["trip"]:
        ingest_trip_updates()
        last_run["trip"] = now

    if now - last_run["alert"] >= POLL_INTERVALS["alert"]:
        ingest_alerts()
        last_run["alert"] = now

    shutdown_event.wait(timeout=1)

print("Productor finalizado correctamente.")