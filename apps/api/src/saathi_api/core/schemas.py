"""Base Pydantic models and the success envelope {data, meta:{nextCursor, requestId}}."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from saathi_api.core.context import current_request_id


class CamelModel(BaseModel):
    """JSON camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )


class Meta(CamelModel):
    request_id: str = Field(default_factory=current_request_id)
    next_cursor: str | None = None


class Envelope[T](CamelModel):
    data: T
    meta: Meta = Field(default_factory=Meta)


class ErrorDetail(CamelModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(CamelModel):
    error: ErrorDetail


def ok[T](data: T, *, next_cursor: str | None = None) -> Envelope[T]:
    return Envelope[T](data=data, meta=Meta(next_cursor=next_cursor))


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorEnvelope} for code in (400, 401, 403, 404, 409, 422, 429, 502, 503)
}
