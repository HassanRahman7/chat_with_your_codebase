"""Health endpoint schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

DependencyState = Literal["ok", "unavailable", "not_checked"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    dependencies: dict[str, DependencyState]
