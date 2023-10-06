import asyncio
import os
from typing import Annotated

from aiokafka import AIOKafkaProducer
from db import ReportRepository
from events import EventManager
from fastapi import FastAPI, Header, Response, WebSocket, WebSocketDisconnect, status
from models import ClickReportRequest, ClickTrackingResult
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

app = FastAPI()

loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=os.getenv("KAFKA_BROKER", ""))
events = EventManager(loop)
db_session = Session(create_engine(os.getenv("DB_URL", "")))
repository = ReportRepository(db_session)
streaming_topic = "clicks"


@app.post("/clicks")
async def register_click(
    request: ClickTrackingResult, user_agent: Annotated[str | None, Header()] = None
):
    value = request.model_copy(update=dict(user_agent=user_agent)).model_dump_json()
    await producer.send(topic=streaming_topic, value=value.encode())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/reports")
async def get_reports(request: ClickReportRequest):
    return repository.get_reports(request.start_time, request.end_time)


@app.websocket("/ws/reports")
async def stream_reports(websocket: WebSocket):
    await events.accept(websocket)
    try:
        while True:
            # keep alive
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        events.unlink(websocket)


@app.on_event("startup")
async def startup_event():
    await producer.start()
    loop.create_task(events.consume())
