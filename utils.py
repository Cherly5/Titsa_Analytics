import json
import uuid
from datetime import datetime
from apache_beam.utils.timestamp import Timestamp
import logging


def build_position_event_payload(v) -> dict:
    """ Construye el payload del evento de posición del vehículo a partir del mensaje protobuf."""
    return {
        "event_id": str(uuid.uuid4()),
        "type": "vehicle_position",
        "vehicle_id": v.vehicle.id,
        "label": v.vehicle.label if v.vehicle.HasField("label") else None,
        "trip_id": v.trip.trip_id,
        "start_time": v.trip.start_time,
        "start_date": v.trip.start_date,
        "schedule_relationship": v.trip.schedule_relationship,
        "route_id": v.trip.route_id,
        "lat": v.position.latitude,
        "lon": v.position.longitude,
        "bearing": v.position.bearing if v.position.HasField("bearing") else None,
        "odometer": v.position.odometer if v.position.HasField("odometer") else None,
        "speed_mps": v.position.speed if v.position.HasField("speed") else None,
        "current_stop_sequence": v.current_stop_sequence if v.HasField("current_stop_sequence") else None,
        "current_status": v.current_status if v.HasField("current_status") else None,
        "timestamp": datetime.utcfromtimestamp(v.timestamp).isoformat() + "Z",
        "stop_id": v.stop_id if v.HasField("stop_id") else None,
        "ingested_at": datetime.utcnow().isoformat() + "Z"
    }

def build_trip_update_event_payload(tu, stu, event_time) -> dict:
    """ Construye el payload del evento de actualización de viaje a partir del mensaje protobuf."""
    return {
        "event_id": str(uuid.uuid4()),
        "type": "trip_update",
        "trip_id": tu.trip.trip_id,
        "start_time": tu.trip.start_time,
        "start_date": tu.trip.start_date,
        "schedule_relationship": tu.trip.schedule_relationship,
        "route_id": tu.trip.route_id,
        "stop_id": stu.stop_id,
        "stop_sequence": stu.stop_sequence,
        "arrival_time": datetime.utcfromtimestamp(stu.arrival.time).isoformat() + "Z" if stu.HasField("arrival") else None,
        "event_time": datetime.utcfromtimestamp(event_time).isoformat() + "Z" if event_time else None,
        "delay": stu.arrival.delay if stu.HasField("arrival") else None,
        "vehicle_id": tu.vehicle.id if tu.HasField("vehicle") else None,
        "vehicle_label": tu.vehicle.label if tu.HasField("vehicle") and tu.vehicle.HasField("label") else None,
        "timestamp": datetime.utcfromtimestamp(tu.timestamp).isoformat() + "Z",
        "ingested_at": datetime.utcnow().isoformat() + "Z"
    }

def build_alert_event_payload(alert) -> dict:
    """ Construye el payload del evento de alerta a partir del mensaje protobuf."""
    return {
        "event_id": str(uuid.uuid4()),
        "type": "alert",
        "cause": alert.cause,
        "effect": alert.effect,
        "ingested_at": datetime.utcnow().isoformat() + "Z"
    }

# --- Funciones de Transformación ---

def parse_json(message):
    return json.loads(message.decode("utf-8"))

def is_valid_event(event):
    return (
            isinstance(event, dict)
            and "event_id" in event
            and "type" in event
    )


def add_latency(event):
    try:
        event_time = datetime.fromisoformat(
            event["timestamp"].replace("Z", "")
        )
        ingested_time = datetime.fromisoformat(
            event["ingested_at"].replace("Z", "")
        )
        event["latency_seconds"] = (
                ingested_time - event_time
        ).total_seconds()
    except Exception:
        event["latency_seconds"] = None

    return event


def add_speed_kmh(event):
    if "speed_mps" in event and event["speed_mps"] is not None:
        event["speed_kmh"] = event["speed_mps"] * 3.6
    else:
        event["speed_kmh"] = None
    return event

def format_vehicle_for_bq(event):
    """
    Formatea el evento mapeando los campos del JSON al esquema exacto
    de la tabla vehicle_positions en BigQuery.
    """
    return {
        "event_id": event.get("event_id"),
        "type": event.get("type"),
        "vehicle_id": event.get("vehicle_id"),
        "label": event.get("label"),
        "trip_id": event.get("trip_id"),
        "start_time": event.get("start_time"),
        "start_date": event.get("start_date"),
        "schedule_relationship": event.get("schedule_relationship"),
        "route_id": event.get("route_id"),
        "lat": event.get("lat"),
        "lon": event.get("lon"),
        "bearing": event.get("bearing"),
        "odometer": event.get("odometer"),
        "speed_mps": event.get("speed_mps"),
        "current_stop_sequence": event.get("current_stop_sequence"),
        "current_status": event.get("current_status"),
        "timestamp": to_bq_timestamp(event.get("timestamp")) if event.get("timestamp") else None,
        "stop_id": event.get("stop_id"),
        "ingested_at": to_bq_timestamp(event.get("ingested_at")) if event.get("ingested_at") else None,
        "speed_kmh": event.get("speed_kmh"),
        "latency_seconds": event.get("latency_seconds")
    }


def format_trip_update_for_bq(event):
    """
    Formatea el evento mapeando los campos del JSON al esquema exacto
    de la tabla trip_updates en BigQuery.
    """
    return {
        "event_id": event.get("event_id"),
        "type": event.get("type"),
        "trip_id": event.get("trip_id"),
        "start_time": event.get("start_time"),
        "start_date": event.get("start_date"),
        "schedule_relationship": event.get("schedule_relationship"),
        "route_id": event.get("route_id"),
        "stop_id": event.get("stop_id"),
        "stop_sequence": event.get("stop_sequence"),
        "arrival_time": to_bq_timestamp(event.get("arrival_time")) if event.get("arrival_time") else None,
        "event_time": to_bq_timestamp(event.get("event_time")) if event.get("event_time") else None,
        "delay": event.get("delay"),
        "vehicle_id": event.get("vehicle_id"),
        "vehicle_label": event.get("vehicle_label"),
        "timestamp": to_bq_timestamp(event.get("timestamp")) if event.get("timestamp") else None,
        "ingested_at": to_bq_timestamp(event.get("ingested_at")) if event.get("ingested_at") else None
    }


def to_bq_timestamp(ts):
    if ts is None:
        return None
    try:
        # Reemplazar la Z por +00:00 para que Python lo detecte como UTC oficial
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return Timestamp.from_utc_datetime(dt)
    except Exception as e:
        logging.error(f"ERROR PARSE DATE: Received value -> '{ts}'. Cause: {e}")
        return None