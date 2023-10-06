import asyncio
import json
import os
from typing import Annotated, Any

import pydantic
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, Header, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from models import ClickTrackingResult

live_report_topic = "live_report"


class EventManager:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.active_connections: list[WebSocket] = []
        self.consumer = AIOKafkaConsumer(
            live_report_topic,
            loop=loop,
            bootstrap_servers=os.getenv("KAFKA_BROKER", ""),
        )

    async def accept(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_text("")

    def unlink(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def consume(self):
        await self.consumer.start()
        try:
            async for msg in self.consumer:
                print(msg)
                await self.broadcast(json.loads(msg.value))  # type: ignore
        finally:
            await self.consumer.stop()

    async def broadcast(self, message: Any):
        for connection in self.active_connections:
            await connection.send_json(message)
