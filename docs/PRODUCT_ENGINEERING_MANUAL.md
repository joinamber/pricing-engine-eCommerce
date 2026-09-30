# Competitive Pricing Engine — Product & Engineering Manual

## Product definition

CPE continuously observes comparable competitor offers for priority iStudio SKUs and maintains a competitive price subject to commercial and operational constraints.

## MVP scope

- Singapore / SGD
- 30 verified iStudio Apple-centric SKUs
- COURTS Singapore as first real competitor
- controlled fixture source
- Streamlit operator UI
- mock publication only

## Product loop

Observe -> understand offer -> identify SKU -> determine market price -> determine allowed price -> human govern exceptions -> publish/verify -> monitor.

## Module model

1. Market Intelligence
2. Offer Intelligence
3. Product Identity
4. Market Price
5. Pricing Decision
6. Governance & Approval
7. Publication
8. Monitoring & Evaluation

## Core rules

- Match lowest eligible comparable landed price; no automatic undercut in MVP.
- Landed competitor price = item price + mandatory shipping - unconditional public promotion.
- MVP contribution-margin floor = 10%, with configurable category/SKU overrides.
- Tier A freshness target = 15 minutes; Tier B = 60 minutes; auto-repricing evidence expires at 2x cadence, capped at 120 minutes.
- Exact trusted identifiers may auto-accept after deterministic validation. Probabilistic mapping is review-only during prototype.
- Automatic decrease <=5%; increase <=10%; otherwise human review.
- Hard violations are blocked, not reviewable.
- Core SLO target: P95 <=15 minutes and P99 <=30 minutes from usable observation to verified publication, excluding human wait; 99.9% monthly core availability.

## Human / agent / deterministic boundary

Agents interpret uncertain market data. Deterministic services control money. Model output may not directly publish prices.

## Open decisions

MAP source-of-truth by supplier, exact legal/source policy per market, and some advanced marketplace/condition rules remain deployment decisions outside this prototype.
