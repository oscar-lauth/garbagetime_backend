import asyncio
import json
import base64, struct
import os
from dotenv import load_dotenv
from threading import Thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
from motor.motor_asyncio import AsyncIOMotorClient

latest_mqtt_value = None

def on_message(client, userdata, message):
    global latest_mqtt_value
    message_str = message.payload.decode("utf-8")
    message_json = json.loads(message_str)
    encoded_payload = message_json["uplink_message"]["frm_payload"]
    raw_payload = base64.b64decode(encoded_payload)
    float_value = struct.unpack('!f',raw_payload[1:])[0]
    latest_mqtt_value = {"ID":raw_payload[0],"Distance":float_value}

def create_app():
    app = FastAPI()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    load_dotenv()
    client.username_pw_set(os.getenv('MQTT_USER'), os.getenv('MQTT_PWD'))
    client.tls_set()
    client.connect(os.getenv('MQTT_ADDR'), 8883)
# Subscribe to the MQTT topic and start the MQTT client loop
    client.on_message = on_message
    client.subscribe("v3/+/devices/+/up")
    client.loop_start()

    @app.get("/")
    async def root():
        return {"value": latest_mqtt_value}

    return app

app = create_app()
origins = [os.getenv('FRONTEND_URL')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(os.getenv("DB_URI"))
    # app.mongodb = app.mongodb_client[settings.db_name]


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()


@app.get("/")
async def root():
    return {"Hello": "World"}

@app.get("/data")
async def get_data():
    return {"value": latest_mqtt_value}

