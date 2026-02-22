"""Testes para scripts/price_cache.py"""
import json
import types
from datetime import datetime, timezone, timedelta

import pytest
import price_cache as pc


# ---------------------------------------------------------------------------
# parse_price_pt
# ---------------------------------------------------------------------------

class TestParsePricePt:
    def test_comma_decimal(self):
        assert pc.parse_price_pt("2,49 €") == 2.49

    def test_comma_decimal_no_symbol(self):
        assert pc.parse_price_pt("0,99") == 0.99

    def test_thousands_separator(self):
        assert pc.parse_price_pt("1.299,00 €") == 1299.0

    def test_integer_price(self):
        assert pc.parse_price_pt("3 €") == 3.0

    def test_empty_string(self):
        assert pc.parse_price_pt("") is None

    def test_none_input(self):
        assert pc.parse_price_pt(None) is None

    def test_whitespace_trimmed(self):
        assert pc.parse_price_pt("  1,50 €  ") == 1.5


# ---------------------------------------------------------------------------
# normalize_key
# ---------------------------------------------------------------------------

class TestNormalizeKey:
    def test_lowercase(self):
        assert pc.normalize_key("Leite Meio-Gordo") == "leite meio-gordo"

    def test_strips_whitespace(self):
        assert pc.normalize_key("  arroz  ") == "arroz"


# ---------------------------------------------------------------------------
# is_cache_valid
# ---------------------------------------------------------------------------

class TestIsCacheValid:
    def _entry(self, hours_ago: float) -> dict:
        ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        return {"cached_at": ts, "price": 1.0}

    def test_fresh_entry_valid(self):
        assert pc.is_cache_valid(self._entry(1)) is True

    def test_old_entry_invalid(self):
        assert pc.is_cache_valid(self._entry(25)) is False

    def test_exactly_at_ttl_invalid(self):
        assert pc.is_cache_valid(self._entry(24.01)) is False

    def test_missing_cached_at(self):
        assert pc.is_cache_valid({"price": 1.0}) is False


# ---------------------------------------------------------------------------
# fuzzy_search
# ---------------------------------------------------------------------------

class TestFuzzySearch:
    def _cache(self):
        now = datetime.now(timezone.utc).isoformat()
        return {
            "continente": {
                "leite meio-gordo": {"name": "Leite Meio-Gordo", "price": 1.29, "cached_at": now},
                "leite uht": {"name": "Leite UHT", "price": 0.99, "cached_at": now},
                "ovos": {"name": "Ovos M 12un", "price": 2.49, "cached_at": now},
            },
            "pingodoce": {}
        }

    def test_finds_exact_match(self):
        results = pc.fuzzy_search(self._cache(), "continente", "ovos")
        assert len(results) >= 1
        assert results[0]["name"] == "Ovos M 12un"

    def test_finds_substring_match(self):
        results = pc.fuzzy_search(self._cache(), "continente", "leite")
        assert len(results) == 2

    def test_no_match_returns_empty(self):
        results = pc.fuzzy_search(self._cache(), "continente", "chocolate")
        assert results == []

    def test_respects_limit(self):
        results = pc.fuzzy_search(self._cache(), "continente", "leite", limit=1)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# cmd_update / cmd_get (integration with temp files)
# ---------------------------------------------------------------------------

class TestCacheUpdateGet:
    @pytest.fixture(autouse=True)
    def patch_cache_file(self, tmp_path, monkeypatch):
        """Redirecionar CACHE_FILE para ficheiro temporário."""
        tmp_cache = tmp_path / "price_cache.json"
        monkeypatch.setattr(pc, "CACHE_FILE", tmp_cache)
        monkeypatch.setattr(pc, "DATA_DIR", tmp_path)

    def _make_update_args(self, market, product, data_dict):
        return types.SimpleNamespace(market=market, product=product, data=json.dumps(data_dict))

    def _make_get_args(self, market, product):
        return types.SimpleNamespace(market=market, product=product)

    def test_update_and_get(self):
        update_args = self._make_update_args(
            "continente", "leite mimosa",
            {"price": 1.29, "unit": "L", "brand": "Mimosa", "available": True}
        )
        result = pc.cmd_update(update_args)
        assert result["updated"] == "leite mimosa"

        get_args = self._make_get_args("continente", "leite mimosa")
        entry = pc.cmd_get(get_args)
        assert entry["found"] is True
        assert entry["price"] == 1.29
        assert entry["valid"] is True

    def test_update_invalid_json_syntax(self):
        # JSON com sintaxe inválida (não parseable)
        args = types.SimpleNamespace(market="continente", product="leite", data="{not valid json")
        result = pc.cmd_update(args)
        assert "error" in result

    def test_update_invalid_json_not_dict(self):
        # JSON válido mas não é objeto (é uma lista)
        args = types.SimpleNamespace(market="continente", product="leite", data='["leite", "ovos"]')
        result = pc.cmd_update(args)
        assert "error" in result

    def test_get_missing_product(self):
        get_args = self._make_get_args("continente", "produto-inexistente")
        result = pc.cmd_get(get_args)
        assert result["found"] is False
