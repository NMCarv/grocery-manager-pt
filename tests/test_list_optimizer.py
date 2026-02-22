"""Testes para scripts/list_optimizer.py"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import list_optimizer as lo


FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inventory(shopping_list=None):
    return {"version": 1, "shopping_list": shopping_list or [], "items": []}


def _model(products=None):
    return products or {}


def _prefs(weekly_limit=150, bulk_limit=120, next_bulk=None):
    return {
        "budget": {"weekly_limit_eur": weekly_limit, "bulk_monthly_budget_eur": bulk_limit},
        "next_bulk_date": next_bulk,
        "bulk_interval_days": 30,
    }


# ---------------------------------------------------------------------------
# generate_weekly_list
# ---------------------------------------------------------------------------

class TestGenerateWeeklyList:
    @pytest.fixture(autouse=True)
    def patch_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lo, "DATA_DIR", tmp_path)
        self.tmp = tmp_path

    def _write(self, inventory=None, model=None, prefs=None):
        (self.tmp / "inventory.json").write_text(json.dumps(inventory or _inventory()))
        (self.tmp / "consumption_model.json").write_text(json.dumps(model or {}))
        (self.tmp / "family_preferences.json").write_text(json.dumps(prefs or _prefs()))

    def test_empty_inputs_returns_empty_list(self):
        self._write()
        result = lo.generate_weekly_list()
        assert result["total_items"] == 0

    def test_manual_items_included(self):
        inv = _inventory([
            {"name": "Leite", "category": "lacticínios", "quantity": {"value": 6, "unit": "L"}}
        ])
        self._write(inventory=inv)
        result = lo.generate_weekly_list()
        assert result["total_items"] == 1
        assert result["manual_items"] == 1

    def test_predicted_items_added_when_stock_low(self):
        model = {
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 3,  # <= 9 → incluir
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.6,  # >= 0.5 → incluir
                "active": True,
                "bulk_eligible": False,
            }
        }
        self._write(model=model)
        result = lo.generate_weekly_list()
        assert result["predicted_items"] == 1
        assert result["total_items"] == 1

    def test_predicted_items_skipped_when_stock_ok(self):
        model = {
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 15,  # > 9 → não incluir
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.6,
                "active": True,
                "bulk_eligible": False,
            }
        }
        self._write(model=model)
        result = lo.generate_weekly_list()
        assert result["predicted_items"] == 0

    def test_low_confidence_predictions_skipped(self):
        model = {
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.3,  # < 0.5 → skip
                "active": True,
                "bulk_eligible": False,
            }
        }
        self._write(model=model)
        result = lo.generate_weekly_list()
        assert result["predicted_items"] == 0

    def test_manual_items_take_priority_over_predictions(self):
        """Se um item já está na lista manual, não deve ser duplicado como previsão."""
        inv = _inventory([
            {"name": "Leite", "category": "lacticínios", "quantity": {"value": 6, "unit": "L"}}
        ])
        model = {
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
            }
        }
        self._write(inventory=inv, model=model)
        result = lo.generate_weekly_list()
        # Deve ter só 1 item (manual), não duplicado
        leite_items = [i for i in result["items"] if "leite" in i["name"].lower() or "Leite" in i["name"]]
        assert len(leite_items) == 1

    def test_inactive_products_not_predicted(self):
        model = {
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.8,
                "active": False,  # inativo
                "bulk_eligible": False,
            }
        }
        self._write(model=model)
        result = lo.generate_weekly_list()
        assert result["predicted_items"] == 0


# ---------------------------------------------------------------------------
# generate_bulk_list
# ---------------------------------------------------------------------------

class TestGenerateBulkList:
    @pytest.fixture(autouse=True)
    def patch_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lo, "DATA_DIR", tmp_path)
        self.tmp = tmp_path

    def _write(self, model=None, prefs=None):
        (self.tmp / "consumption_model.json").write_text(json.dumps(model or {}))
        (self.tmp / "family_preferences.json").write_text(json.dumps(prefs or _prefs()))

    def test_bulk_eligible_products_included(self):
        model = {
            "arroz": {
                "name": "Arroz",
                "category": "conservas",
                "avg_weekly_consumption": {"value": 2.0, "unit": "kg"},
                "confidence": 0.6,
                "active": True,
                "bulk_eligible": True,
            }
        }
        self._write(model=model)
        result = lo.generate_bulk_list()
        assert result["total_items"] == 1
        # Quantidade deve ser ~4.5 semanas de consumo
        item = result["items"][0]
        assert item["quantity"]["value"] == pytest.approx(2.0 * lo.BULK_WEEKS, abs=0.1)

    def test_non_bulk_eligible_excluded(self):
        model = {
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.6,
                "active": True,
                "bulk_eligible": False,
            }
        }
        self._write(model=model)
        result = lo.generate_bulk_list()
        assert result["total_items"] == 0

    def test_bulk_quantity_overrides_calculation(self):
        model = {
            "arroz": {
                "name": "Arroz",
                "category": "conservas",
                "avg_weekly_consumption": {"value": 2.0, "unit": "kg"},
                "confidence": 0.6,
                "active": True,
                "bulk_eligible": True,
                "bulk_quantity": {"value": 10.0, "unit": "kg"},  # Override
            }
        }
        self._write(model=model)
        result = lo.generate_bulk_list()
        assert result["items"][0]["quantity"]["value"] == 10.0


# ---------------------------------------------------------------------------
# generate_triage
# ---------------------------------------------------------------------------

class TestGenerateTriage:
    @pytest.fixture(autouse=True)
    def patch_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lo, "DATA_DIR", tmp_path)
        self.tmp = tmp_path
        # Defaults
        (self.tmp / "inventory.json").write_text(json.dumps(_inventory()))
        (self.tmp / "consumption_model.json").write_text(json.dumps({}))
        (self.tmp / "family_preferences.json").write_text(json.dumps(_prefs()))

    def test_triage_has_correct_structure(self):
        result = lo.generate_triage()
        assert "weekly_items" in result
        assert "bulk_items" in result
        assert "type" in result
        assert result["type"] == "triage"

    def test_bulk_items_separated_when_near_bulk_date(self):
        """Items bulk_eligible devem ir para bulk_items quando granel está próximo (≤7 dias)."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "arroz": {
                "name": "Arroz",
                "category": "conservas",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 2.0, "unit": "kg"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": True,
            }
        }))
        next_bulk = (datetime.now(timezone.utc) + timedelta(days=5)).date().isoformat()
        result = lo.generate_triage(next_bulk_date=next_bulk)
        assert result["total_bulk"] == 1
        assert result["total_weekly"] == 0

    def test_bulk_items_in_weekly_when_bulk_far(self):
        """Items bulk_eligible mas granel distante → compra semanal normal."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "arroz": {
                "name": "Arroz",
                "category": "conservas",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 2.0, "unit": "kg"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": True,
            }
        }))
        next_bulk = (datetime.now(timezone.utc) + timedelta(days=20)).date().isoformat()
        result = lo.generate_triage(next_bulk_date=next_bulk)
        assert result["total_weekly"] == 1
        assert result["total_bulk"] == 0
