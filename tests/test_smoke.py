from decimal import Decimal
from pathlib import Path

from app.core import compute_price, normalize_offer, exact_map
from app.identity import retrieve
from app.models import PriceInput, RawOffer
from app.service import Engine

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_has_30_verified_rows():
    engine = Engine(str(ROOT / "data" / "catalog.csv"))
    assert len(engine.catalog) == 30
    assert all(s.istudio_sku for s in engine.catalog)


def test_exact_id_maps_to_internal_sku():
    engine = Engine(str(ROOT / "data" / "catalog.csv"))
    raw = RawOffer(
        title="AirPods 4 ANC",
        manufacturer_part_number="MXP93ZA/A",
        item_price_sgd=Decimal("239"),
    )
    result = exact_map(normalize_offer(raw), engine.catalog)
    assert result.decision.value == "MATCH"
    assert result.sku_id == "P015"
    assert result.route == "EXACT_ID"


def test_retrieval_handles_storage_variant():
    engine = Engine(str(ROOT / "data" / "catalog.csv"))
    candidates = retrieve(
        "13-inch MacBook Air M5",
        "16GB;1TB;Starlight",
        engine.catalog,
        3,
    )
    assert candidates
    assert candidates[0][1] == "P002"


def test_pricing_respects_margin_floor():
    decision = compute_price(
        PriceInput(
            current_price_sgd=Decimal("100"),
            market_price_sgd=Decimal("70"),
            cost_sgd=Decimal("90"),
        )
    )
    assert decision.candidate_price_sgd == Decimal("100.00")
    assert "MARGIN_FLOOR" in decision.reasons
