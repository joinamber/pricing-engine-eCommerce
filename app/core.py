from decimal import Decimal, ROUND_HALF_UP
from .models import *

def money(x: Decimal)->Decimal:
    return x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def normalize_offer(raw:RawOffer)->NormalizedOffer:
    if raw.currency != 'SGD': raise ValueError('M1 supports SGD only')
    landed=money(raw.item_price_sgd + raw.shipping_sgd - raw.unconditional_discount_sgd)
    if landed < 0: raise ValueError('landed price cannot be negative')
    return NormalizedOffer(source_id=raw.source_id,manufacturer_part_number=raw.manufacturer_part_number,
        title=raw.title,landed_price_sgd=landed,currency=raw.currency,availability=raw.availability,
        observed_at=raw.observed_at,evidence_fresh=raw.evidence_fresh)

def exact_map(offer:NormalizedOffer, catalog:list[CatalogSKU])->MappingResult:
    mpn=(offer.manufacturer_part_number or '').strip().upper()
    if not mpn: return MappingResult(decision='ABSTAIN',route='EXACT_ID',reason='MISSING_IDENTIFIER')
    hits=[s for s in catalog if s.istudio_sku.strip().upper()==mpn]
    if len(hits)==1: return MappingResult(decision='MATCH',sku_id=hits[0].prototype_id,route='EXACT_ID',reason='EXACT_MANUFACTURER_PART_NUMBER')
    if len(hits)>1: return MappingResult(decision='ABSTAIN',route='EXACT_ID',reason='DUPLICATE_IDENTIFIER')
    return MappingResult(decision='NO_MATCH',route='EXACT_ID',reason='IDENTIFIER_NOT_IN_CATALOG')

def eligible_market_price(offers:list[NormalizedOffer])->Decimal|None:
    valid=[o.landed_price_sgd for o in offers if o.availability==Availability.IN_STOCK and o.evidence_fresh]
    return min(valid) if valid else None

def compute_price(inp:PriceInput)->PriceDecision:
    margin_floor=money(inp.cost_sgd / (Decimal('1')-inp.margin_floor_pct))
    floor=margin_floor; applied='MARGIN_FLOOR' if inp.market_price_sgd < margin_floor else None
    if inp.map_price_sgd is not None and inp.map_price_sgd > floor:
        floor=inp.map_price_sgd
        if inp.market_price_sgd < inp.map_price_sgd: applied='MAP_FLOOR'
    candidate=money(max(inp.market_price_sgd,floor))
    reasons=[]
    if applied: reasons.append(applied)
    if not inp.evidence_fresh:
        return PriceDecision(candidate_price_sgd=candidate,market_price_sgd=inp.market_price_sgd,
            margin_floor_price_sgd=margin_floor,applied_floor=applied,policy_decision='BLOCK',reasons=['STALE_EVIDENCE'])
    change=(candidate-inp.current_price_sgd)/inp.current_price_sgd if inp.current_price_sgd else Decimal('0')
    if change < Decimal('-0.05') or change > Decimal('0.10'):
        reasons.append('PRICE_CHANGE_BOUND'); decision='REVIEW'
    else:
        reasons.append('WITHIN_AUTO_BOUNDS'); decision='ALLOW'
    return PriceDecision(candidate_price_sgd=candidate,market_price_sgd=inp.market_price_sgd,
        margin_floor_price_sgd=margin_floor,applied_floor=applied,policy_decision=decision,reasons=reasons)
