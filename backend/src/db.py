from dataclasses import dataclass
from datetime import datetime

from models import ClickReport, ClickReportRequest, ClickReportResponse
from sqlalchemy import TIMESTAMP, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    column_property,
    mapped_column,
)
from sqlalchemy.sql import func as F


class Base(DeclarativeBase):
    ...


class ReportModel(Base):
    __tablename__ = "clicks"
    timestamp: Mapped[int] = mapped_column(
        name="timestamp", type_=TIMESTAMP, primary_key=True
    )
    product_id: Mapped[str] = mapped_column(
        name="product_id", type_=String(64), primary_key=True
    )
    device: Mapped[str] = mapped_column(name="device", type_=String, primary_key=True)

    minute_truncated = column_property(F.date_trunc("minute", timestamp))


@dataclass
class ReportRepository:
    session: Session

    def get_reports(self, start_time: datetime, end_time: datetime):
        start_time = start_time.replace(second=0, microsecond=0)
        end_time = end_time.replace(second=0, microsecond=0)
        result = (
            self.session.query(
                ReportModel.minute_truncated.label("time"),
                ReportModel.product_id,
                ReportModel.device,
                F.count(ReportModel.minute_truncated).label("clicks"),
            )
            .filter(ReportModel.timestamp.between(start_time, end_time))
            .group_by(
                ReportModel.minute_truncated, ReportModel.product_id, ReportModel.device
            )
            .all()
        )
        return ClickReportResponse(
            request=ClickReportRequest(start_time=start_time, end_time=end_time),
            reports=[
                ClickReport(
                    time=time,
                    product_id=product_id,
                    device=device,
                    clicks=clicks,
                )
                for time, product_id, device, clicks in result
            ],
        )
