from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from html import unescape
from urllib.request import Request, urlopen
from .models import Availability, RawOffer
from .core import money

class CourtsExtractionError(ValueError): pass
class CourtsDeliveryError(ValueError): pass

@dataclass(frozen=True)
class RawSourceSnapshot:
    source_url: str
    captured_at: datetime
    http_status: int
    body_hash: str
    raw_html: str

@dataclass(frozen=True)
class CourtsOffer:
    title: str
    manufacturer_part_number: str
    courts_sku: str | None
    item_price_sgd: Decimal
    rrp_sgd: Decimal | None
    availability: Availability
    delivery_mode: str
    shipping_sgd: Decimal
    source_url: str
    body_hash: str
    captured_at: datetime

ECONOMY_CATEGORIES = {'Mac','iPad','Audio','Accessory-IT'}

def capture(url:str, timeout:int=20)->RawSourceSnapshot:
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 CPE-MVP/0.2'})
    with urlopen(req,timeout=timeout) as r:
        body=r.read().decode('utf-8','replace'); status=getattr(r,'status',200)
    return RawSourceSnapshot(url,datetime.now(timezone.utc),status,hashlib.sha256(body.encode()).hexdigest(),body)

def snapshot_from_html(url:str, html:str, captured_at:datetime|None=None)->RawSourceSnapshot:
    return RawSourceSnapshot(url,captured_at or datetime.now(timezone.utc),200,hashlib.sha256(html.encode()).hexdigest(),html)

def _text(html:str)->str:
    t=re.sub(r'<script[^>]*>.*?</script>',' ',html,flags=re.I|re.S)
    t=re.sub(r'<style[^>]*>.*?</style>',' ',t,flags=re.I|re.S)
    return re.sub(r's+',' ',unescape(re.sub(r'<[^>]+>',' ',t))).strip()

def _jsonld(html:str)->list[dict]:
    out=[]
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',html,re.I|re.S):
        try:
            obj=json.loads(unescape(m.group(1)).strip())
            if isinstance(obj,list): out.extend(x for x in obj if isinstance(x,dict))
            elif isinstance(obj,dict): out.append(obj)
        except Exception: pass
    return out

def _product_jsonld(html:str)->dict:
    for obj in _jsonld(html):
        if obj.get('@type')=='Product': return obj
        graph=obj.get('@graph',[])
        if isinstance(graph,list):
            for x in graph:
                if isinstance(x,dict) and x.get('@type')=='Product': return x
    return {}

def _price(v)->Decimal|None:
    if v is None: return None
    m=re.search(r'(\d[\d,]*(?:\.\d{1,2})?)',str(v))
    return Decimal(m.group(1).replace(',','')) if m else None

def classify_delivery(category:str, item_price:Decimal)->tuple[str,Decimal]:
    if category in ECONOMY_CATEGORIES:
        return 'ECONOMY', Decimal('0.00') if item_price >= Decimal('99') else Decimal('5.90')
    if not category:
        raise CourtsDeliveryError('DELIVERY_CATEGORY_UNKNOWN')
    return 'STANDARD', Decimal('5.90') if item_price >= Decimal('200') else Decimal('30.00')

def extract(snapshot:RawSourceSnapshot, category:str)->CourtsOffer:
    if snapshot.http_status != 200: raise CourtsExtractionError(f'HTTP_{snapshot.http_status}')
    html=snapshot.raw_html; text=_text(html); p=_product_jsonld(html)
    title=str(p.get('name') or '')
    if not title:
        m=re.search(r'<title[^>]*>(.*?)</title>',html,re.I|re.S); title=_text(m.group(1)) if m else ''
    mpn=str(p.get('mpn') or p.get('sku') or '').strip()
    if not mpn:
        m=re.search(r'\b(?:MPN|Model|Manufacturer Part Number)\s*[:#]?\s*([A-Z0-9]+(?:[-/][A-Z0-9]+)+)',text,re.I)
        if m: mpn=m.group(1)
    if not mpn:
        m=re.search(r'\b([A-Z0-9]{5,}(?:ZA|ZP|PA|AM|FE|X)/A)\b',text,re.I)
        if m: mpn=m.group(1).upper()
    m=re.search(r'data-(?:current-)?price=["\']([\d,.]+)["\']',html,re.I)
    price=_price(m.group(1)) if m else None
    offers=p.get('offers') if isinstance(p,dict) else None
    if price is None and isinstance(offers,dict): price=_price(offers.get('price'))
    if price is None:
        m=re.search(r'(?:Now|Our Price|Price)\s*[: ]*S?\$\s*([\d,.]+)',text,re.I); price=_price(m.group(1)) if m else None
    if price is None:
        m=re.search(r'\bS\$\s*([\d,.]+)',text,re.I); price=_price(m.group(1)) if m else None
    rrp=None
    m=re.search(r'(?:RRP|Regular Price|Usual Price)\s*[: ]*S?\$\s*([\d,.]+)',text,re.I)
    if m: rrp=_price(m.group(1))
    courts_sku=None
    m=re.search(r'\bIP\d{5,}\b',snapshot.source_url+' '+text,re.I)
    if m: courts_sku=m.group(0).upper()
    avail=Availability.UNKNOWN
    avail_src=''
    if isinstance(offers,dict): avail_src=str(offers.get('availability') or '')
    combined=(avail_src+' '+text).lower()
    if any(x in combined for x in ['outofstock','out of stock','currently unavailable','not available']): avail=Availability.OUT_OF_STOCK
    elif any(x in combined for x in ['instock','in stock','add to cart','add-to-cart']): avail=Availability.IN_STOCK
    elif any(x in combined for x in ['backorder','pre-order','pre order','indent basis']): avail=Availability.BACKORDER
    if not title: raise CourtsExtractionError('MISSING_TITLE')
    if not mpn: raise CourtsExtractionError('MISSING_MANUFACTURER_PART_NUMBER')
    if price is None: raise CourtsExtractionError('MISSING_CURRENT_PRICE')
    mode, shipping=classify_delivery(category,price)
    return CourtsOffer(title,mpn,courts_sku,money(price),money(rrp) if rrp is not None else None,avail,mode,money(shipping),snapshot.source_url,snapshot.body_hash,snapshot.captured_at)

def to_raw_offer(o:CourtsOffer)->RawOffer:
    return RawOffer(source_id='COURTS_SG',manufacturer_part_number=o.manufacturer_part_number,title=o.title,
        item_price_sgd=o.item_price_sgd,shipping_sgd=o.shipping_sgd,currency='SGD',availability=o.availability,
        observed_at=o.captured_at,evidence_fresh=True)
