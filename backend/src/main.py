import asyncio
import json
import os
import re
from datetime import datetime
from threading import Thread
from typing import Any
from fastapi.responses import StreamingResponse

import pydantic
import uvicorn
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, status
from pydantic.alias_generators import to_camel

app = FastAPI()

loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=os.getenv("KAFKA_BROKER", ""))
stream_analytics_topic = "stream_analytics"
live_report_topic = "live_report"


class ClickTrackingResult(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=to_camel)
    session_id: str
    timestamp: datetime
    product_id: str
    user_agent: str

    @property
    def device(self):
        # Regular expressions to identify common User-Agent patterns
        ios_pattern = r"iPhone|iPad|iPod|iOS"
        android_pattern = r"Android"
        windows_pattern = r"Windows"
        macos_pattern = r"Macintosh|Mac OS X"
        user_agent = self.user_agent

        # Check for iOS
        if re.search(ios_pattern, user_agent, re.I):
            return "iOS"

        # Check for Android
        if re.search(android_pattern, user_agent, re.I):
            return "Android"

        # Check for Windows
        if re.search(windows_pattern, user_agent):
            return "Windows"

        # Check for MacOS
        if re.search(macos_pattern, user_agent, re.I):
            return "MacOS"

        # If no match is found, classify as 'Other'
        return "Other"


@app.post("/")
async def register_click(request: ClickTrackingResult):
    value = request.model_dump_json()
    await producer.send(topic=stream_analytics_topic, value=value.encode())
    # await producer.send(topic=live_report_topic, value=value.encode())
    print("......")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class ClickReportRequest(pydantic.BaseModel):
    ...


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.consumer = AIOKafkaConsumer(
            live_report_topic,
            loop=loop,
            bootstrap_servers=os.getenv("KAFKA_BROKER", ""),
        )

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_text("")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def consume(self):
        await self.consumer.start()
        try:
            async for msg in self.consumer:
                print(msg)
                await self.broadcast(json.loads(str(msg.value)))
        finally:
            await self.consumer.stop()

    async def broadcast(self, message: Any):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.post("/reports")
async def get_reports(request: ClickReportRequest):
    return {}


@app.websocket("/ws/reports")
async def stream_reports(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep alive
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/streaming")
async def streaming_example():
    async def generator():
        for i in range(100):
            yield f"reload time {i}\n"
            await asyncio.sleep(1)
    return StreamingResponse(generator(), media_type="text/event-stream")


@app.on_event("startup")
async def startup_event():
    await producer.start()
    loop.create_task(manager.consume())


# def main():
    # producer.send(topic=stream_analytics_topic, value=b"Hello Kafka!")
    # producer.flush()

    # uvicorn.run(app, host="0.0.0.0")
