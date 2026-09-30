from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field

class Availability(str, Enum):
    IN_STOCK='IN_STOCK'; OUT_OF_STOCK='OUT_OF_STOCK'; BACKORDER='BACKORDER'; UNKNOWN='UNKNOWN'
class MappingDecision(str, Enum):
    MATCH='MATCH'; NO_MATCH='NO_MATCH'; ABSTAIN='ABSTAIN'
class PolicyDecision(str, Enum):
    ALLOW='ALLOW'; REVIEW='REVIEW'; BLOCK='BLOCK'

class CatalogSKU(BaseModel):
    prototype_id:str; category:str; product_name:str; variant:str; istudio_sku:str
    current_price_sgd:Decimal; list_price_sgd:Decimal|None=None; availability:Availability=Availability.UNKNOWN

class RawOffer(BaseModel):
    source_id:str='fixture'; manufacturer_part_number:str|None=None; title:str
    item_price_sgd:Decimal=Field(ge=0); shipping_sgd:Decimal=Field(default=Decimal('0'),ge=0)
    unconditional_discount_sgd:Decimal=Field(default=Decimal('0'),ge=0)
    currency:str='SGD'; availability:Availability=Availability.IN_STOCK
    observed_at:datetime=Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_fresh:bool=True

class NormalizedOffer(BaseModel):
    source_id:str; manufacturer_part_number:str|None; title:str; landed_price_sgd:Decimal
    currency:str; availability:Availability; observed_at:datetime; evidence_fresh:bool

class MappingResult(BaseModel):
    decision:MappingDecision; sku_id:str|None=None; route:str; reason:str

class PriceInput(BaseModel):
    current_price_sgd:Decimal; market_price_sgd:Decimal; cost_sgd:Decimal
    margin_floor_pct:Decimal=Decimal('0.10'); map_price_sgd:Decimal|None=None; evidence_fresh:bool=True

class PriceDecision(BaseModel):
    candidate_price_sgd:Decimal; market_price_sgd:Decimal; margin_floor_price_sgd:Decimal
    applied_floor:str|None=None; policy_decision:PolicyDecision; reasons:list[str]

class Publication(BaseModel):
    sku_id:str; price_sgd:Decimal; status:str; verified:bool=False

class AuditEvent(BaseModel):
    event_type:str; sku_id:str|None=None; detail:dict; at:datetime=Field(default_factory=lambda: datetime.now(timezone.utc))
