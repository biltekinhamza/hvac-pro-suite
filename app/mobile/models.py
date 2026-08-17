from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ActivationRequest(BaseModel):
    activation_code: str = Field(min_length=1, max_length=256)
    device_id: str = Field(min_length=1, max_length=200)
    device_name: str = Field(default="", max_length=200)


class DraftItem(BaseModel):
    part_code: str = Field(min_length=1, max_length=100)
    inputs: dict[str, object] = Field(default_factory=dict)
    quantity: int = Field(default=1, ge=1, le=100000)


class DraftPayload(BaseModel):
    local_id: str = Field(min_length=1, max_length=100)
    customer_name: str = Field(default="", max_length=300)
    customer_phone: str = Field(min_length=7, max_length=30)
    profit_rate: float = Field(default=0, ge=0, le=10000)
    shipping_amount: float = Field(default=0, ge=0)
    items: list[DraftItem] = Field(default_factory=list, max_length=500)


class OperationRequest(BaseModel):
    operation_id: str = Field(min_length=8, max_length=100)
    type: Literal["sync_draft", "submit_quote"]
    draft: DraftPayload
