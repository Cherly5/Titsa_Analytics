import asyncio
import json
import math
from datetime import datetime

import websockets
from google.cloud import pubsub_v1

from config import PROJECT_ID, WEBSOCKET_SUBSCRIPTION_ID, WS_HOST, WS_PORT, BEARING_USE, INTERPOLATION_USE

buses_cache = {}
connected_clients = set()
running = True

def calculate_bus_status(vehicle_data):
    """
    Calcula el estado del vehículo en función del dígito
    0: INCOMING_AT, 1: STOPPED_AT, 2: IN_TRANSIT_TO
    """
    status_code = vehicle_data.get("current_status")

    if status_code == 0:
        return "llegando"
    elif status_code == 1:
        return "en_parada"
    elif status_code == 2:
        return "en_transito"
    else:
        return "desconocido"


def transform_vehicle_for_map(vehicle_data):
    """
    Transforma el formato del productor al formato que espera el mapa.
    """
    try:
        speed_kmh = vehicle_data.get("speed_kmh")

        if speed_kmh is None:
            if vehicle_data.get("speed_mps") is not None:
                speed_kmh = vehicle_data["speed_mps"] * 3.6
            else:
                speed_kmh = 0.0

        vehicle_id = vehicle_data.get("vehicle_id", "UNKNOWN")

        native_bearing = vehicle_data.get("bearing")

        if native_bearing is not None and BEARING_USE:
            print(f"Using native bearing for vehicle {vehicle_id}: {native_bearing}°")
            heading = native_bearing

        elif vehicle_id not in buses_cache:
            heading = 0

        else:
            prev = buses_cache[vehicle_id]

            delta_lat = vehicle_data.get("lat", 0) - prev.get("lat", 0)
            delta_lon = vehicle_data.get("lon", 0) - prev.get("lng", 0)

            if delta_lat == 0 and delta_lon == 0:
                heading = prev.get("heading", 0)
            else:
                heading = (90 - math.degrees(math.atan2(delta_lat, delta_lon))) % 360

        estado = calculate_bus_status(vehicle_data)

        timestamp_str = vehicle_data.get("timestamp", "")
        try:
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                timestamp_ms = int(dt.timestamp() * 1000)
            else:
                timestamp_ms = int(datetime.now().timestamp() * 1000)
        except Exception as exception:
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            print(f"Error parsing timestamp for vehicle {vehicle_id}: {exception}. Using current time.")

        transformed = {
            "id": vehicle_id,
            "lat": vehicle_data.get("lat", 0),
            "lng": vehicle_data.get("lon", 0),
            "heading": round(heading, 1),
            "velocidad": round(speed_kmh, 1) if speed_kmh else 0,
            "linea": str(vehicle_data.get("route_id", "N/A")),
            "viaje": str(vehicle_data.get("trip_id", "N/A")),
            "estado": estado,
            "proxima_parada": vehicle_data.get("stop_id", "N/A"),
            "numero_parada": vehicle_data.get("current_stop_sequence", "N/A"),
            "timestamp": timestamp_ms
        }

        buses_cache[vehicle_id] = transformed

        return transformed

    except Exception as exception:
        print(f"Error transforming vehicle {vehicle_data.get('vehicle_id')}: {exception}")
        return None


batch_queue = []


def pubsub_callback(message):
    """Callback que recibe mensajes y los encola para procesar por lotes"""
    try:
        data = message.data.decode("utf-8")
        vehicle_data = json.loads(data)

        if vehicle_data.get("type") != "vehicle_position":
            message.ack()
            return

        bus_for_map = transform_vehicle_for_map(vehicle_data)

        if bus_for_map:
            batch_queue.append(bus_for_map)

        message.ack()

    except Exception as exception:
        print(f"Callback error: {exception}")
        message.ack()


async def broadcast_batches():
    """Agrupa las actualizaciones y las envía a todos los clientes cada segundo"""
    global batch_queue

    while running:
        await asyncio.sleep(1.0)

        if not batch_queue:
            continue

        current_batch = batch_queue[:]
        batch_queue.clear()

        if not connected_clients:
            continue
        message_to_send = json.dumps(current_batch)
        await asyncio.gather(*(client.send(message_to_send) for client in connected_clients))

        print(f"Batch sent: {len(current_batch)} grouped updates.")


async def garbage_collector():
    """Limpia guaguas que llevan más de 15 minutos sin emitir datos"""
    while running:
        await asyncio.sleep(300)
        now_ms = int(datetime.now().timestamp() * 1000)
        obsolete_limit = 15 * 60 * 1000

        stale_buses = [vid for vid, bus in buses_cache.items() if (now_ms - bus['timestamp']) > obsolete_limit]

        for vid in stale_buses:
            del buses_cache[vid]

        if stale_buses:
            print(f"GC: {len(stale_buses)} inactive buses removed from memory.")

async def send_full_state(websocket):
    """Envía el estado completo de todos los buses a un nuevo cliente"""
    if buses_cache:
        all_buses = list(buses_cache.values())
        await websocket.send(json.dumps(all_buses))
        print(f"Initial status sent with {len(all_buses)} buses")


async def websocket_handler(websocket):
    """Maneja conexiones WebSocket del frontend"""
    connected_clients.add(websocket)
    print(f"Client connected. Total: {len(connected_clients)}")

    try:
        await websocket.send(json.dumps({
            "type": "connection",
            "status": "connected",
            "message": "Real-time connection",
            "mode": "production",
            "interpolation_use": INTERPOLATION_USE,
            "bearing_use": BEARING_USE
        }))
        await send_full_state(websocket)
        await websocket.wait_closed()
    except Exception as exception:
        print(f"Client Error: {exception}")
    finally:
        connected_clients.remove(websocket)
        print(f"Client disconnection. Total: {len(connected_clients)}")


async def shutdown():
    """Cierra el servidor limpiamente"""
    global running
    print("\nShutting down server...")
    running = False

    if connected_clients:
        close_tasks = [client.close() for client in connected_clients]
        await asyncio.gather(*close_tasks)
    print("Server shutdown complete.")


async def main():
    global running

    print("Starting WebSocket server")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, WEBSOCKET_SUBSCRIPTION_ID)
    loop = asyncio.get_running_loop()

    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=lambda msg: pubsub_callback(msg)
    )

    print(f"Subscribed to Pub/Sub - Receiving data from producer")

    asyncio.create_task(broadcast_batches())
    asyncio.create_task(garbage_collector())

    print(f"Websocket Server at ws://{WS_HOST}:{WS_PORT}")
    try:
        async with websockets.serve(websocket_handler, WS_HOST, WS_PORT):
            while running:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nInterrupt received")
    finally:
        streaming_pull_future.cancel()
        subscriber.close()
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"\nFatal error: {e}")