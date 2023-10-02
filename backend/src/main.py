import os
import re
from datetime import datetime
from typing import Any

import kafka
import pydantic
import uvicorn
from fastapi import FastAPI, Response, status
from pydantic.alias_generators import to_camel

app = FastAPI()

producer = kafka.KafkaProducer(
    bootstrap_servers=[os.getenv("KAFKA_BROKER")]
)
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
def register_click(request: ClickTrackingResult):
    value = request.model_dump_json()
    producer.send(topic=stream_analytics_topic, value=value)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def main():
    producer.send(topic=stream_analytics_topic, value=b"Hello Kafka!")
    producer.flush()

    uvicorn.run(app)
