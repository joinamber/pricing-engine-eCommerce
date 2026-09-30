from pathlib import Path
import sys, csv, uuid
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import streamlit as st
from app.service import Engine
from app.models import RawOffer, PriceInput
from app.core import normalize_offer, exact_map, compute_price
from app.identity import retrieve
from app.review import ReviewStore

st.set_page_config(page_title='Competitive Pricing Engine',layout='wide')
engine=Engine(str(ROOT/'data/catalog.csv'))
store=ReviewStore(str(ROOT/'data/m4_reviews.sqlite3'))
pricing=list(csv.DictReader(open(ROOT/'data/m2_shipping_pricing.csv',encoding='utf-8')))
by_id={r['prototype_id']:r for r in pricing}

st.title('Competitive Pricing Engine — Operator Prototype')
page=st.sidebar.radio('Workspace',['Pricing Overview','Mapping Review','Price Review','Evaluation','Audit'])

if page=='Pricing Overview':
    rows=[]
    for s in engine.catalog:
        r=by_id.get(s.prototype_id,{})
        rows.append({'SKU':s.prototype_id,'Product':s.product_name,'Variant':s.variant,'iStudio landed':r.get('istudio_final_price_sgd'),'COURTS landed':r.get('courts_final_price_sgd'),'Competitive':r.get('competitive_final_price_sgd'),'Source':r.get('competitive_source'),'COURTS availability':r.get('courts_availability')})
    st.dataframe(rows,use_container_width=True,hide_index=True)

elif page=='Mapping Review':
    st.subheader('Mapping Review Queue')
    title=st.text_input('Competitor title','Apple 13-inch MacBook Air M5')
    variant=st.text_input('Observed attributes','16GB;1TB;Starlight')
    mpn=st.text_input('Manufacturer part number (optional)','')
    candidates=retrieve(title,variant,engine.catalog,5)
    if mpn:
        offer=normalize_offer(RawOffer(title=title,manufacturer_part_number=mpn,item_price_sgd=Decimal('1')))
        exact=exact_map(offer,engine.catalog)
        st.info(f'Exact-ID route: {exact.decision.value} — {exact.sku_id or exact.reason}')
    st.markdown('#### Candidate products')
    for score,pid,s in candidates:
        st.write(f'**{pid}** — {s.product_name} — {s.variant} — retrieval score {score:.3f}')
    ids=[x[1] for x in candidates]
    shadow=st.selectbox('AI shadow suggestion',['ABSTAIN']+[f'MATCH {x}' for x in ids]+['NO_MATCH'])
    conf=st.slider('Shadow confidence',0.0,1.0,0.80,0.01)
    decision=st.radio('Human decision',['MATCH','NO_MATCH','INSUFFICIENT_EVIDENCE'],horizontal=True)
    selected=st.selectbox('Confirmed SKU',[None]+ids,disabled=decision!='MATCH')
    reason=st.selectbox('Reason',['IDENTITY_CONFIRMED','CRITICAL_ATTRIBUTE_MISMATCH','INSUFFICIENT_EVIDENCE','OTHER'])
    if st.button('Save mapping review',type='primary'):
        md='MATCH' if shadow.startswith('MATCH') else shadow
        ms=shadow.split(' ',1)[1] if shadow.startswith('MATCH') else None
        rid=store.save_mapping_review(observation_id=str(uuid.uuid4()),competitor_title=title,candidate_ids=ids,model_decision=md,model_selected_sku=ms,model_confidence=conf,human_decision='ABSTAIN' if decision=='INSUFFICIENT_EVIDENCE' else decision,human_selected_sku=selected,reason_code=reason,model_version='shadow-manual',prompt_version='mapping-v1')
        st.success(f'Review saved: {rid}. Model output remains non-authoritative.')

elif page=='Price Review':
    st.subheader('Deterministic Price Review')
    pid=st.selectbox('SKU',[s.prototype_id for s in engine.catalog])
    s=next(x for x in engine.catalog if x.prototype_id==pid)
    r=by_id[pid]
    market=Decimal(r['competitive_final_price_sgd']); current=Decimal(r['istudio_final_price_sgd'])
    cost=st.number_input('Fixture variable cost (SGD)',min_value=0.0,value=float(current*Decimal('0.70')),step=1.0)
    mapv=st.number_input('MAP floor (0 = none)',min_value=0.0,value=0.0,step=1.0)
    pd=compute_price(PriceInput(current_price_sgd=current,market_price_sgd=market,cost_sgd=Decimal(str(cost)),map_price_sgd=Decimal(str(mapv)) if mapv else None))
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Current landed','S$%.2f' % current)
    c2.metric('Market landed','S$%.2f' % market)
    c3.metric('Candidate','S$%.2f' % pd.candidate_price_sgd)
    c4.metric('Policy',pd.policy_decision.value)
    st.write('Reasons:',', '.join(pd.reasons))
    action=st.radio('Operator action',['APPROVE','REJECT'],horizontal=True)
    if st.button('Record price decision',type='primary'):
        rid=store.save_price_review(sku_id=pid,current_price_sgd=current,market_price_sgd=market,candidate_price_sgd=pd.candidate_price_sgd,policy_decision=pd.policy_decision.value,reasons=pd.reasons,human_decision=action)
        if action=='APPROVE':
            pub=store.publish_mock(pid,pd.candidate_price_sgd); st.success(f'Approved and mock-published; verified. Publication {pub}')
        else:
            st.warning(f'Rejected. Review {rid}')

elif page=='Evaluation':
    st.subheader('Shadow Evaluation')
    m=store.mapping_metrics(); cols=st.columns(6)
    labels=['Labeled cases','MATCH precision','False-match rate','Resolution rate','Abstention rate','Auto publications']
    vals=[m['labeled_cases'],m['model_match_precision'],m['false_match_rate'],m['resolution_rate'],m['abstention_rate'],m['model_auto_publications']]
    for c,l,v in zip(cols,labels,vals):
        c.metric(l,'—' if v is None else (f'{v:.1%}' if isinstance(v,float) else v))
    st.caption('Metrics are meaningful only after human-reviewed real observations accumulate.')
else:
    st.subheader('Audit Trail')
    st.dataframe([{'event':a,'entity':b,'detail':c,'at':d} for a,b,c,d in store.audit()],use_container_width=True,hide_index=True)
