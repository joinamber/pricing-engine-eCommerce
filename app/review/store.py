from __future__ import annotations
import json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS mapping_reviews(
 review_id TEXT PRIMARY KEY, observation_id TEXT NOT NULL, competitor_title TEXT NOT NULL,
 candidate_ids_json TEXT NOT NULL, model_decision TEXT, model_selected_sku TEXT, model_confidence REAL,
 human_decision TEXT NOT NULL, human_selected_sku TEXT, reason_code TEXT NOT NULL,
 evidence_hash TEXT, model_version TEXT, prompt_version TEXT, reviewed_by TEXT NOT NULL,
 reviewed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS price_reviews(
 review_id TEXT PRIMARY KEY, sku_id TEXT NOT NULL, current_price_sgd REAL NOT NULL,
 market_price_sgd REAL NOT NULL, candidate_price_sgd REAL NOT NULL, policy_decision TEXT NOT NULL,
 reasons_json TEXT NOT NULL, human_decision TEXT NOT NULL, reviewed_by TEXT NOT NULL, reviewed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS publications(
 publication_id TEXT PRIMARY KEY, sku_id TEXT NOT NULL, price_sgd REAL NOT NULL,
 status TEXT NOT NULL, verified INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events(
 event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, entity_id TEXT, detail_json TEXT NOT NULL, created_at TEXT NOT NULL
);
'''

def _now(): return datetime.now(timezone.utc).isoformat()

class ReviewStore:
    def __init__(self, path:str):
        Path(path).parent.mkdir(parents=True, exist_ok=True); self.path=path
        with sqlite3.connect(path) as c: c.executescript(SCHEMA)

    def _audit(self,c,event_type,entity_id,detail):
        c.execute('INSERT INTO audit_events VALUES (?,?,?,?,?)',(str(uuid.uuid4()),event_type,entity_id,json.dumps(detail,sort_keys=True),_now()))

    def save_mapping_review(self, *, observation_id, competitor_title, candidate_ids, human_decision, reason_code,
                            human_selected_sku=None, model_decision=None, model_selected_sku=None, model_confidence=None,
                            evidence_hash=None, model_version=None, prompt_version=None, reviewed_by='operator'):
        rid=str(uuid.uuid4()); at=_now()
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO mapping_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
                rid,observation_id,competitor_title,json.dumps(candidate_ids),model_decision,model_selected_sku,model_confidence,
                human_decision,human_selected_sku,reason_code,evidence_hash,model_version,prompt_version,reviewed_by,at))
            self._audit(c,'MAPPING_REVIEWED',rid,{'human_decision':human_decision,'human_selected_sku':human_selected_sku})
        return rid

    def save_price_review(self, *, sku_id,current_price_sgd,market_price_sgd,candidate_price_sgd,policy_decision,reasons,human_decision,reviewed_by='operator'):
        rid=str(uuid.uuid4()); at=_now()
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO price_reviews VALUES (?,?,?,?,?,?,?,?,?,?)',(rid,sku_id,float(current_price_sgd),float(market_price_sgd),float(candidate_price_sgd),policy_decision,json.dumps(reasons),human_decision,reviewed_by,at))
            self._audit(c,'PRICE_REVIEWED',rid,{'sku_id':sku_id,'human_decision':human_decision})
        return rid

    def publish_mock(self, sku_id, price_sgd):
        pid=str(uuid.uuid4()); at=_now()
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO publications VALUES (?,?,?,?,?,?)',(pid,sku_id,float(price_sgd),'PUBLISHED',1,at))
            self._audit(c,'PRICE_PUBLISHED',pid,{'sku_id':sku_id,'price_sgd':float(price_sgd),'verified':True})
        return pid

    def mapping_metrics(self):
        with sqlite3.connect(self.path) as c:
            rows=c.execute('SELECT model_decision,model_selected_sku,human_decision,human_selected_sku FROM mapping_reviews').fetchall()
        n=len(rows)
        model_matches=[r for r in rows if r[0]=='MATCH']
        correct=sum(1 for r in model_matches if r[2]=='MATCH' and r[1]==r[3])
        false=sum(1 for r in model_matches if not (r[2]=='MATCH' and r[1]==r[3]))
        abstain=sum(1 for r in rows if r[0]=='ABSTAIN')
        resolved=sum(1 for r in rows if r[0] in ('MATCH','NO_MATCH'))
        return {
            'labeled_cases':n,
            'model_match_precision': correct/len(model_matches) if model_matches else None,
            'false_match_rate': false/len(model_matches) if model_matches else None,
            'resolution_rate': resolved/n if n else None,
            'abstention_rate': abstain/n if n else None,
            'human_review_rate': 1.0 if n else None,
            'model_auto_publications':0
        }

    def audit(self):
        with sqlite3.connect(self.path) as c:
            return c.execute('SELECT event_type,entity_id,detail_json,created_at FROM audit_events ORDER BY created_at DESC').fetchall()
