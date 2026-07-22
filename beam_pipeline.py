import os

import apache_beam as beam
from apache_beam.io.gcp.bigquery import WriteToBigQuery
from apache_beam.options.pipeline_options import GoogleCloudOptions, StandardOptions
from apache_beam.options.pipeline_options import PipelineOptions
from dotenv import load_dotenv

from utils import *

load_dotenv()

options = PipelineOptions()

google_cloud_options = options.view_as(GoogleCloudOptions)
google_cloud_options.project = os.getenv("GOOGLE_CLOUD_PROJECT", "tfg-movilidad-titsa")
google_cloud_options.job_name = "titsa-streaming-job"
google_cloud_options.temp_location = "gs://tfg-titsa-bucket/temp"
google_cloud_options.region = "europe-west1"

standard_options = options.view_as(StandardOptions)
standard_options.streaming = True
google_cloud_options.enable_streaming_engine = True

PROJECT_ID = google_cloud_options.project
BQ_DATASET= os.getenv("BIG_QUERY_DATASET_ID", "titsa_dataset")
BQ_TABLE_VEHICLES= os.getenv("BQ_TABLE_VEHICLES", "vehicle_positions")
BQ_TABLE_TRIPS= os.getenv("BQ_TABLE_TRIPS", "trip_updates")

VEHICLES_SUB_NAME = os.getenv("DATAFLOW_PUBSUB_SUBSCRIPTION", "titsa-dataflow-vehicles-sub")

SUBSCRIPTION_VEHICLES = f"projects/{PROJECT_ID}/subscriptions/{VEHICLES_SUB_NAME}"
SUBSCRIPTION_TRIPS = f"projects/{PROJECT_ID}/subscriptions/trip-updates-sub"

VEHICLE_SCHEMA = os.getenv('VEHICLE_SCHEMA', "event_id:STRING,type:STRING,vehicle_id:STRING,label:STRING,trip_id:STRING,start_time:STRING,start_date:STRING,schedule_relationship:INTEGER,route_id:STRING,lat:FLOAT,lon:FLOAT,bearing:FLOAT,odometer:FLOAT,speed_mps:FLOAT,current_stop_sequence:INTEGER,current_status:STRING,timestamp:TIMESTAMP,stop_id:STRING,ingested_at:TIMESTAMP")
TRIP_SCHEMA = os.getenv('TRIP_SCHEMA', "event_id:STRING,type:STRING,trip_id:STRING,start_time:STRING,start_date:STRING,schedule_relationship:INTEGER,route_id:STRING,stop_id:STRING,stop_sequence:INTEGER,arrival_time:TIMESTAMP,event_time:TIMESTAMP,delay:INTEGER,vehicle_id:STRING,vehicle_label:STRING,timestamp:TIMESTAMP,ingested_at:TIMESTAMP")

def run():
    with beam.Pipeline(options=options) as p:
        # Leer de Pub/Sub de ambas suscripciones
        vehicles_raw = p | "ReadVehicles" >> beam.io.ReadFromPubSub(subscription=SUBSCRIPTION_VEHICLES)
        trips_raw = p | "ReadTrips" >> beam.io.ReadFromPubSub(subscription=SUBSCRIPTION_TRIPS)

        # Unir los mensajes y aplicar el parseo y validación general
        events = (
                (vehicles_raw, trips_raw)
                | "MergeStreams" >> beam.Flatten()
                | "ParseJSON" >> beam.Map(parse_json)
                | "Validate" >> beam.Filter(is_valid_event)
        )

        # Enriquecimiento común
        enriched_events = (
                events
                | "AddLatency" >> beam.Map(add_latency)
        )

        # Separar Vehicle Positions
        vehicle_events = (
                enriched_events
                | "FilterVehicleEvents" >> beam.Filter(
            lambda e: e["type"] == "vehicle_position"
        )
                | "AddSpeedKmh" >> beam.Map(add_speed_kmh)
        )

        # Preparar para BigQuery (Vehículos)
        vehicle_bq = (
                vehicle_events
                | "FormatVehicleForBQ" >> beam.Map(format_vehicle_for_bq)
        )

        # Escribir en BigQuery (Vehículos) y capturar resultados
        vehicle_bq_result = (
                vehicle_bq | "WriteVehicleToBQ" >> WriteToBigQuery(
            table=f"{PROJECT_ID}:{BQ_DATASET}.{BQ_TABLE_VEHICLES}",
            schema=VEHICLE_SCHEMA,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            method=beam.io.WriteToBigQuery.Method.STORAGE_WRITE_API,
            insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
        )
        )

        # Imprimir en los logs de Dataflow las filas que BigQuery rechazó
        (vehicle_bq_result[beam.io.gcp.bigquery.BigQueryWriteFn.FAILED_ROWS]
         | "LogVehicleBQErrors" >> beam.Map(lambda error: print(f"ERROR BQ VEHICLES: {error}")))

        # Separar Trip Updates
        trip_updates = (
                enriched_events
                | "FilterTripUpdates" >> beam.Filter(lambda e: e["type"] == "trip_update")
                | "FormatTripUpdateForBQ" >> beam.Map(format_trip_update_for_bq)
        )

        # Escribir en BigQuery (Trip Updates) y capturar resultados
        trip_bq_result = (
                trip_updates | "WriteTripUpdatesToBQ" >> WriteToBigQuery(
            table=f"{PROJECT_ID}:{BQ_DATASET}.{BQ_TABLE_TRIPS}",
            schema=TRIP_SCHEMA,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            method=beam.io.WriteToBigQuery.Method.STORAGE_WRITE_API,
            insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
        )
        )

        # Imprimir en los logs de Dataflow las filas que BigQuery rechazó
        (trip_bq_result[beam.io.gcp.bigquery.BigQueryWriteFn.FAILED_ROWS]
         | "LogTripBQErrors" >> beam.Map(lambda error: print(f"ERROR BQ TRIPS: {error}")))

if __name__ == "__main__":
    run()