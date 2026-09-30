import csv
from decimal import Decimal
from .models import *
from .core import normalize_offer, exact_map, eligible_market_price, compute_price

class Engine:
    def __init__(self,catalog_path:str):
        self.catalog=self._load(catalog_path); self.store={s.prototype_id:s.current_price_sgd for s in self.catalog}; self.audit=[]
    def _load(self,path):
        out=[]
        with open(path,newline='',encoding='utf-8') as f:
            for r in csv.DictReader(f):
                out.append(CatalogSKU(prototype_id=r['prototype_id'],category=r['category'],product_name=r['product_name'],variant=r['variant'],istudio_sku=r['istudio_sku'],current_price_sgd=Decimal(r['current_price_sgd']),list_price_sgd=Decimal(r['list_price_sgd']) if r['list_price_sgd'] else None,availability=r['availability']))
        return out
    def run(self, raw:RawOffer, cost_sgd:Decimal, map_price_sgd:Decimal|None=None, margin_floor_pct:Decimal=Decimal('0.10')):
        offer=normalize_offer(raw); mapping=exact_map(offer,self.catalog)
        self.audit.append(AuditEvent(event_type='OFFER_NORMALIZED',sku_id=mapping.sku_id,detail=offer.model_dump(mode='json')))
        self.audit.append(AuditEvent(event_type='MAPPING_DECIDED',sku_id=mapping.sku_id,detail=mapping.model_dump(mode='json')))
        if mapping.decision != MappingDecision.MATCH: return {'mapping':mapping,'terminal_state':'NOT_PUBLISHED'}
        market=eligible_market_price([offer])
        if market is None: return {'mapping':mapping,'terminal_state':'NO_ELIGIBLE_MARKET_PRICE'}
        sku=next(s for s in self.catalog if s.prototype_id==mapping.sku_id)
        pd=compute_price(PriceInput(current_price_sgd=sku.current_price_sgd,market_price_sgd=market,cost_sgd=cost_sgd,map_price_sgd=map_price_sgd,margin_floor_pct=margin_floor_pct,evidence_fresh=offer.evidence_fresh))
        self.audit.append(AuditEvent(event_type='PRICE_DECIDED',sku_id=sku.prototype_id,detail=pd.model_dump(mode='json')))
        if pd.policy_decision != PolicyDecision.ALLOW: return {'mapping':mapping,'market_price_sgd':market,'price_decision':pd,'terminal_state':pd.policy_decision.value}
        pub=Publication(sku_id=sku.prototype_id,price_sgd=pd.candidate_price_sgd,status='PUBLISHED')
        self.store[sku.prototype_id]=pd.candidate_price_sgd; pub.verified=self.store[sku.prototype_id]==pd.candidate_price_sgd
        self.audit.append(AuditEvent(event_type='PRICE_PUBLISHED',sku_id=sku.prototype_id,detail=pub.model_dump(mode='json')))
        return {'mapping':mapping,'market_price_sgd':market,'price_decision':pd,'publication':pub,'terminal_state':'VERIFIED' if pub.verified else 'VERIFICATION_FAILED'}
