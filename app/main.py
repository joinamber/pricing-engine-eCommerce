from decimal import Decimal
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from .models import RawOffer
from .service import Engine

app=FastAPI(title='Competitive Pricing Engine',version='0.1.0')
engine=Engine(str(Path(__file__).resolve().parents[1]/'data'/'catalog.csv'))

class RunRequest(BaseModel):
    offer:RawOffer
    cost_sgd:Decimal
    map_price_sgd:Decimal|None=None
    margin_floor_pct:Decimal=Decimal('0.10')

@app.get('/health')
def health(): return {'status':'ok','catalog_size':len(engine.catalog)}

@app.get('/catalog')
def catalog(): return engine.catalog

@app.post('/run')
def run(req:RunRequest): return engine.run(req.offer,req.cost_sgd,req.map_price_sgd,req.margin_floor_pct)

@app.get('/audit')
def audit(): return engine.audit
