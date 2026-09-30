from __future__ import annotations
import re
from difflib import SequenceMatcher
from .models import CatalogSKU

FAMILIES=[('macbook air','macbook_air'),('macbook pro','macbook_pro'),('macbook neo','macbook_neo'),('ipad mini','ipad_mini'),('ipad air','ipad_air'),('ipad pro','ipad_pro'),('airpods pro','airpods_pro'),('airpods','airpods'),('earpods','earpods'),('apple watch ultra','watch_ultra'),('apple watch se','watch_se'),('apple pencil','apple_pencil'),('power adapter','power_adapter'),('magsafe charger','magsafe_charger'),('airtag','airtag'),('apple tv','apple_tv'),('magic mouse','magic_mouse')]

def family(text):
    t=text.lower()
    for key,val in FAMILIES:
        if key in t:return val
    return 'unknown'

def attrs(text):
    t=text.lower(); out={}
    for k,pat in [('storage',r'(128gb|256gb|512gb|1tb)'),('memory',r'(8gb|16gb|24gb)'),('screen',r'(11|13|14|15|40|44|49)[- ]?(?:inch|mm|")'),('wattage',r'(20w|35w)')]:
        m=re.search(pat,t); out[k]=m.group(1) if m else None
    out['cellular']='cellular' in t
    out['anc']='active noise cancellation' in t or re.search(r'anc',t) is not None
    return out

def retrieve(title, variant, catalog:list[CatalogSKU], k=5):
    q=f'{title} {variant}'; qf=family(q); qa=attrs(q); scored=[]
    for s in catalog:
        txt=f'{s.product_name} {s.variant}'; sf=family(txt); sa=attrs(txt)
        if qf!='unknown' and sf!=qf: continue
        contradiction=False; bonus=0.0
        for key in ('storage','memory','screen','wattage'):
            if qa[key] and sa[key] and qa[key]!=sa[key]: contradiction=True
            elif qa[key] and sa[key] and qa[key]==sa[key]: bonus+=0.12
        for key in ('cellular','anc'):
            if qa[key]!=sa[key] and (qa[key] or sa[key]): contradiction=True
        if contradiction: continue
        sim=SequenceMatcher(None,q.lower(),txt.lower()).ratio()
        scored.append((sim+bonus,s.prototype_id,s))
    scored.sort(key=lambda x:(-x[0],x[1])); return scored[:k]
