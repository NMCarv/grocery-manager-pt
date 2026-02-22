"""Testes para scripts/price_compare.py"""
import pytest
import price_compare as pc


# ---------------------------------------------------------------------------
# calculate_delivery
# ---------------------------------------------------------------------------

class TestCalculateDelivery:
    def test_continente_free_above_threshold(self):
        assert pc.calculate_delivery("continente", 60.0) == 0.0

    def test_continente_paid_below_threshold(self):
        assert pc.calculate_delivery("continente", 30.0) == pc.DELIVERY_CONFIG["continente"]["cost"]

    def test_pingodoce_free_above_threshold(self):
        assert pc.calculate_delivery("pingodoce", 100.0) == 0.0

    def test_pingodoce_paid_below_threshold(self):
        cost = pc.calculate_delivery("pingodoce", 50.0)
        assert cost == pc.DELIVERY_CONFIG["pingodoce"]["cost"]

    def test_unknown_market_returns_zero(self):
        assert pc.calculate_delivery("auchan", 30.0) == 0.0


# ---------------------------------------------------------------------------
# apply_coupons
# ---------------------------------------------------------------------------

class TestApplyCoupons:
    def test_applies_simple_coupon(self):
        coupons = [{"description": "3€ em >50€", "discount_eur": 3.0, "min_spend": 50.0, "categories": []}]
        discount, applied = pc.apply_coupons(60.0, coupons, {"lacticínios"})
        assert discount == 3.0
        assert len(applied) == 1

    def test_does_not_apply_below_min_spend(self):
        coupons = [{"description": "3€ em >50€", "discount_eur": 3.0, "min_spend": 50.0, "categories": []}]
        discount, applied = pc.apply_coupons(30.0, coupons, {"lacticínios"})
        assert discount == 0.0
        assert applied == []

    def test_category_restriction_blocks_coupon(self):
        coupons = [{"description": "2€ em limpeza", "discount_eur": 2.0, "min_spend": 0.0, "categories": ["limpeza"]}]
        discount, applied = pc.apply_coupons(50.0, coupons, {"lacticínios"})
        assert discount == 0.0

    def test_category_restriction_allows_coupon(self):
        coupons = [{"description": "2€ em limpeza", "discount_eur": 2.0, "min_spend": 0.0, "categories": ["limpeza"]}]
        discount, applied = pc.apply_coupons(50.0, coupons, {"limpeza", "frescos"})
        assert discount == 2.0

    def test_multiple_coupons_applied_greedy(self):
        coupons = [
            {"description": "5€", "discount_eur": 5.0, "min_spend": 0.0, "categories": []},
            {"description": "2€", "discount_eur": 2.0, "min_spend": 0.0, "categories": []},
        ]
        discount, applied = pc.apply_coupons(20.0, coupons, set())
        assert discount == 7.0
        assert len(applied) == 2
        # Maior primeiro
        assert applied[0]["discount_eur"] == 5.0

    def test_discount_capped_at_subtotal(self):
        coupons = [{"description": "100€", "discount_eur": 100.0, "min_spend": 0.0, "categories": []}]
        discount, _ = pc.apply_coupons(10.0, coupons, set())
        assert discount == 10.0

    def test_no_coupons(self):
        discount, applied = pc.apply_coupons(50.0, [], set())
        assert discount == 0.0
        assert applied == []


# ---------------------------------------------------------------------------
# optimize_split
# ---------------------------------------------------------------------------

def _make_item(name, category, continente_price, pingodoce_price=None, available=True):
    prices = {}
    if continente_price is not None:
        prices["continente"] = {
            "price": continente_price,
            "promo_effective_price": None,
            "available": available,
        }
    if pingodoce_price is not None:
        prices["pingodoce"] = {
            "price": pingodoce_price,
            "promo_effective_price": None,
            "available": True,
        }
    return {
        "item": {"name": name, "category": category, "quantity": {"value": 1, "unit": "un"}},
        "prices": prices,
    }


class TestOptimizeSplit:
    def test_assigns_to_cheaper_market(self):
        items = [
            _make_item("leite", "lacticínios", continente_price=1.29, pingodoce_price=1.50),
            _make_item("arroz", "conservas", continente_price=0.99, pingodoce_price=0.79),
        ]
        result = pc.optimize_split(items)
        assert "continente" in result["markets"]
        assert "pingodoce" in result["markets"]
        # Leite mais barato no continente, arroz mais barato no pingo doce
        cont_names = [i["name"] for i in result["markets"]["continente"]["items"]]
        pd_names = [i["name"] for i in result["markets"]["pingodoce"]["items"]]
        assert "leite" in cont_names
        assert "arroz" in pd_names

    def test_single_market_when_only_one_available(self):
        items = [_make_item("leite", "lacticínios", continente_price=1.29, pingodoce_price=None)]
        result = pc.optimize_split(items)
        assert "continente" in result["markets"]
        assert "pingodoce" not in result["markets"]

    def test_unavailable_goes_to_unavailable_list(self):
        items = [_make_item("produto-raro", "outros", continente_price=None, pingodoce_price=None)]
        result = pc.optimize_split(items)
        assert len(result["unavailable"]) == 1
        assert result["unavailable"][0]["name"] == "produto-raro"

    def test_total_is_sum_of_market_totals(self):
        items = [
            _make_item("leite", "lacticínios", continente_price=1.29, pingodoce_price=1.50),
        ]
        result = pc.optimize_split(items)
        market_totals = sum(m["total"] for m in result["markets"].values())
        assert abs(result["total"] - market_totals) < 0.01

    def test_alternatives_include_both_markets(self):
        items = [
            _make_item("leite", "lacticínios", continente_price=1.29, pingodoce_price=1.50),
        ]
        result = pc.optimize_split(items)
        strategies = [a["strategy"] for a in result["alternatives"]]
        assert "all_continente" in strategies
        assert "all_pingodoce" in strategies

    def test_applies_coupons(self):
        items = [_make_item("leite", "lacticínios", continente_price=60.0, pingodoce_price=None)]
        market_config = {
            "continente": {
                "coupons": [{"description": "3€", "discount_eur": 3.0, "min_spend": 50.0, "categories": []}],
                "balance": 0.0,
            },
            "pingodoce": {"coupons": [], "balance": 0.0},
        }
        result = pc.optimize_split(items, market_config)
        cont = result["markets"]["continente"]
        assert cont["coupon_discount"] == 3.0
        assert len(cont["coupons_applied"]) == 1

    def test_recommendation_note_when_savings_small(self):
        # Ambos os preços muito similares → deve sugerir single store
        items = [
            _make_item("leite", "lacticínios", continente_price=10.0, pingodoce_price=10.01),
        ]
        result = pc.optimize_split(items)
        # Com diferença mínima, deve haver nota de recomendação
        assert result["recommendation_note"] is not None


# ---------------------------------------------------------------------------
# check_budget
# ---------------------------------------------------------------------------

class TestCheckBudget:
    def test_within_budget(self):
        prefs = {"budget": {"weekly_limit_eur": 150.0}}
        result = pc.check_budget(100.0, prefs)
        assert result["over_budget"] is False
        assert result["over_by"] == 0.0

    def test_over_budget(self):
        prefs = {"budget": {"weekly_limit_eur": 100.0}}
        result = pc.check_budget(120.0, prefs)
        assert result["over_budget"] is True
        assert result["over_by"] == 20.0

    def test_default_budget_when_missing(self):
        result = pc.check_budget(100.0, {})
        assert result["weekly_limit"] == 150.0
