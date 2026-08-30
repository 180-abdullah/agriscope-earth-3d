from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class MissionId(str, Enum):
    FLOOD = "flood-watch"
    CROP_STRESS = "crop-stress"
    LAND_CHANGE = "land-change"
    IRRIGATION = "irrigation"
    CARBON = "carbon"
    FIRE_HEAT = "fire-heat"


class DataStatus(str, Enum):
    OBSERVED = "observed"
    NEAR_REAL_TIME = "near-real-time"
    FORECAST = "forecast"
    MODELLED = "modelled"
    CALCULATED = "calculated"
    USER_SUPPLIED = "user-supplied"
    DEMONSTRATION = "demonstration"
    UNAVAILABLE = "unavailable"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AnalysisRequest(BaseModel):
    mission: MissionId
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    area_hectares: float = Field(default=100.0, gt=0, le=10_000_000)
    analysis_date: date | None = None
    name: str | None = Field(default=None, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parameters")
    @classmethod
    def limit_parameter_count(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 80:
            raise ValueError("A maximum of 80 mission parameters is allowed")
        return value


class Metric(BaseModel):
    key: str
    label: str
    value: float | int | str | None
    unit: str = ""
    interpretation: str = ""


class SourceRecord(BaseModel):
    name: str
    url: str | None = None
    role: str
    status: DataStatus
    spatial_resolution: str | None = None
    temporal_resolution: str | None = None
    note: str | None = None
    identifier: str | None = None
    acquisition_datetime: str | None = None
    accessed_at: str | None = None
    license: str | None = None


class AnalysisResponse(BaseModel):
    analysis_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    methodology_version: str = "ASE-0.3"
    mission: MissionId
    title: str
    coordinates: Coordinates
    area_hectares: float
    score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    summary: str
    data_status: list[DataStatus]
    metrics: list[Metric]
    sources: list[SourceRecord]
    caveats: list[str]
    geometry: dict[str, Any]


class MissionDefinition(BaseModel):
    id: MissionId
    name: str
    short_name: str
    question: str
    description: str
    accent: str
    default_latitude: float
    default_longitude: float
    default_area_hectares: float
    statuses: list[DataStatus]
    required_parameters: list[str] = Field(default_factory=list)


class ExportRequest(BaseModel):
    analysis: AnalysisResponse
    format: str = Field(pattern="^(json|csv|geojson)$")
