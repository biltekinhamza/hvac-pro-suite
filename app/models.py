from __future__ import annotations

from pydantic import BaseModel, Field


class PartField(BaseModel):
    name: str
    label: str


class Part(BaseModel):
    code: str
    group: str
    title: str
    image: str | None = None
    fields: list[PartField]


class CalculateRequest(BaseModel):
    part_code: str
    inputs: dict[str, object] = Field(default_factory=dict)
    quantity: int = Field(default=1, ge=1)
    profit_rate: float = 0


class CartItemRequest(BaseModel):
    part_code: str
    inputs: dict[str, object] = Field(default_factory=dict)
    quantity: int = Field(default=1, ge=1)
    profit_rate: float = 0


class MaterialAvailabilityUpdateRequest(BaseModel):
    is_available: bool


class QuoteCreateRequest(BaseModel):
    customer_name: str = ""
    shipping_amount: float = 0


class QuoteMergeRequest(BaseModel):
    quote_ids: list[int] = Field(min_length=2)


class MaterialCostUpdateRequest(BaseModel):
    average_unit_cost: float = Field(ge=0)


class AddMaterialOptionRequest(BaseModel):
    material_name: str
    option_name: str
    average_unit_cost: float = Field(ge=0)
