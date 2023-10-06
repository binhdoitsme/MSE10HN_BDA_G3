from datetime import datetime, timedelta

import pydantic
from pydantic.alias_generators import to_camel


class ClickTrackingResult(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True, alias_generator=to_camel)
    product_id: str
    timestamp: datetime = pydantic.Field(default_factory=datetime.utcnow)
    user_agent: str = pydantic.Field(default_factory=str)


class ClickReportRequest(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True, alias_generator=to_camel)
    start_time: datetime = pydantic.Field(
        default_factory=lambda: (datetime.utcnow() - timedelta(minutes=30)).replace(
            second=0, microsecond=0
        )
    )
    end_time: datetime = pydantic.Field(
        default_factory=lambda: datetime.utcnow().replace(second=0, microsecond=0)
    )


class ClickReport(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True, alias_generator=to_camel)
    time: datetime  # rounded to minutes
    product_id: str
    device: str
    clicks: int = 0


class ClickReportResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True, alias_generator=to_camel)
    reports: list[ClickReport]
    request: ClickReportRequest
