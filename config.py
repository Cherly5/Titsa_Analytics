import os
from dotenv import load_dotenv

load_dotenv()

# Google Cloud Configuration
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'tfg-movilidad-titsa')
DATAFLOW_SUBSCRIPTION_ID = os.getenv('PUBSUB_DATAFLOW_SUBSCRIPTION', 'titsa-dataflow-vehicles')
WEBSOCKET_SUBSCRIPTION_ID = os.getenv('PUBSUB_WEBSOCKET_SUBSCRIPTION', 'titsa-ws-vehicles')
BEARING_USE = os.getenv('BEARING_USE', 'false').lower() == 'true'
INTERPOLATION_USE = os.getenv('INTERPOLATION_USE', 'true').lower() == 'true'

# WebSocket Configuration
WS_HOST = os.getenv('WS_HOST', 'localhost')
WS_PORT = int(os.getenv('WS_PORT', 8765))

# Mapbox Configuration
MAPBOX_ACCESS_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN', '')

# API Configuration
API_KEY = os.getenv('API_KEY', '')
BASE_URL = os.getenv('BASE_URL', '')

if not MAPBOX_ACCESS_TOKEN:
    print("WARNING: MAPBOX_ACCESS_TOKEN is not set in .env")
    print("The map will not function correctly without a valid token.")

if not PROJECT_ID or ( not DATAFLOW_SUBSCRIPTION_ID or not WEBSOCKET_SUBSCRIPTION_ID):
    print("WARNING: Incomplete Google Cloud configuration")

print("LOADED SETUP:")
print(f"   - Project ID: {PROJECT_ID}")
print(f"   - Dataflow Subscription: {DATAFLOW_SUBSCRIPTION_ID}")
print(f"   - Websocket Subscription: {WEBSOCKET_SUBSCRIPTION_ID}")
print(f"   - WebSocket: {WS_HOST}:{WS_PORT}")
print(f"   - Mapbox Token: {'Checked' if MAPBOX_ACCESS_TOKEN else 'Not checked'}")
print(f"   - API Key: {'Checked' if API_KEY else 'Not checked'}")