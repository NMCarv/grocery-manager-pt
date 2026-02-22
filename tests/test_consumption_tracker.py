"""Testes para scripts/consumption_tracker.py"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import consumption_tracker as ct


# ---------------------------------------------------------------------------
# weighted_average
# ---------------------------------------------------------------------------

class TestWeightedAverage:
    def test_single_value(self):
        assert ct.weighted_average([5.0]) == 5.0

    def test_equal_values(self):
        assert ct.weighted_average([3.0, 3.0, 3.0]) == 3.0

    def test_recent_weighted_more(self):
        # [1.0, 10.0] — mais recente (10.0) deve ter mais peso
        result = ct.weighted_average([1.0, 10.0])
        assert result > 5.5  # Média simples seria 5.5

    def test_empty_returns_zero(self):
        assert ct.weighted_average([]) == 0


# ---------------------------------------------------------------------------
# get_seasonal_factor
# ---------------------------------------------------------------------------

class TestSeasonalFactor:
    def test_returns_1_for_unknown_category(self):
        factor = ct.get_seasonal_factor("lacticínios")
        assert factor == 1.0

    def test_ice_cream_summer(self):
        # Mock o mês para julho
        ct_mod = ct
        orig = ct_mod.datetime
        class MockDatetime:
            @staticmethod
            def now():
                class FakeNow:
                    month = 7
                return FakeNow()
        ct_mod.datetime = MockDatetime
        try:
            factor = ct.get_seasonal_factor("gelados")
            assert factor > 1.0
        finally:
            ct_mod.datetime = orig


# ---------------------------------------------------------------------------
# update_model_after_purchase
# ---------------------------------------------------------------------------

class TestUpdateModelAfterPurchase:
    @pytest.fixture(autouse=True)
    def use_temp_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ct, "MODEL_FILE", tmp_path / "consumption_model.json")
        monkeypatch.setattr(ct, "HISTORY_FILE", tmp_path / "shopping_history.json")
        monkeypatch.setattr(ct, "DATA_DIR", tmp_path)

    def _purchase(self, items, date=None):
        return {
            "date": date or datetime.now(timezone.utc).isoformat(),
            "market": "continente",
            "items": items,
        }

    def test_creates_new_product(self):
        purchase = self._purchase([
            {"name": "Leite", "category": "lacticínios", "quantity": 6, "unit": "L", "price": 7.74}
        ])
        result = ct.update_model_after_purchase(purchase)
        assert result["updated"] == 1

        model = json.loads(ct.MODEL_FILE.read_text())
        assert "leite" in model
        assert model["leite"]["confidence"] > 0

    def test_second_purchase_increases_confidence(self):
        item = {"name": "Leite", "category": "lacticínios", "quantity": 6, "unit": "L", "price": 7.74}

        d1 = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        d2 = datetime.now(timezone.utc).isoformat()

        ct.update_model_after_purchase(self._purchase([item], date=d1))
        ct.update_model_after_purchase(self._purchase([item], date=d2))

        model = json.loads(ct.MODEL_FILE.read_text())
        assert model["leite"]["confidence"] > 0.1

    def test_history_limited_to_12(self):
        item = {"name": "Leite", "category": "lacticínios", "quantity": 6, "unit": "L", "price": 7.74}
        for i in range(15):
            date = (datetime.now(timezone.utc) - timedelta(days=7 * i)).isoformat()
            ct.update_model_after_purchase(self._purchase([item], date=date))

        model = json.loads(ct.MODEL_FILE.read_text())
        assert len(model["leite"]["purchase_history"]) <= 12

    def test_calculates_avg_weekly_after_two_purchases(self):
        item = {"name": "Leite", "category": "lacticínios", "quantity": 6, "unit": "L", "price": 7.74}
        d1 = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        d2 = datetime.now(timezone.utc).isoformat()
        ct.update_model_after_purchase(self._purchase([item], date=d1))
        ct.update_model_after_purchase(self._purchase([item], date=d2))

        model = json.loads(ct.MODEL_FILE.read_text())
        # Com 6L em 7 dias, consumo semanal ≈ 6L/semana
        avg = model["leite"]["avg_weekly_consumption"]["value"]
        assert 4.0 <= avg <= 8.0  # Tolerância razoável


# ---------------------------------------------------------------------------
# check_stock
# ---------------------------------------------------------------------------

class TestCheckStock:
    @pytest.fixture(autouse=True)
    def use_temp_model(self, tmp_path, monkeypatch):
        self.model_file = tmp_path / "consumption_model.json"
        monkeypatch.setattr(ct, "MODEL_FILE", self.model_file)
        monkeypatch.setattr(ct, "DATA_DIR", tmp_path)

    def _write_model(self, data):
        self.model_file.write_text(json.dumps(data))

    def test_alerts_when_stock_low(self):
        last_purchased = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
        self._write_model({
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "last_purchased": last_purchased,
                "last_quantity": 6,
                "confidence": 0.8,
                "active": True,
            }
        })
        result = ct.check_stock()
        # Após 6 dias com 6L semanais (≈0.857L/dia), quase sem stock
        assert result["checked"] == 1
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["product_id"] == "leite"

    def test_no_alert_when_stock_ok(self):
        last_purchased = datetime.now(timezone.utc).isoformat()
        self._write_model({
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "last_purchased": last_purchased,
                "last_quantity": 10,
                "confidence": 0.8,
                "active": True,
            }
        })
        result = ct.check_stock()
        assert len(result["alerts"]) == 0

    def test_skips_low_confidence(self):
        last_purchased = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        self._write_model({
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "last_purchased": last_purchased,
                "last_quantity": 6,
                "confidence": 0.1,  # Abaixo do threshold
                "active": True,
            }
        })
        result = ct.check_stock()
        assert len(result["alerts"]) == 0


# ---------------------------------------------------------------------------
# apply_feedback
# ---------------------------------------------------------------------------

class TestApplyFeedback:
    @pytest.fixture(autouse=True)
    def use_temp_model(self, tmp_path, monkeypatch):
        self.model_file = tmp_path / "consumption_model.json"
        monkeypatch.setattr(ct, "MODEL_FILE", self.model_file)
        monkeypatch.setattr(ct, "DATA_DIR", tmp_path)
        self.model_file.write_text(json.dumps({
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "estimated_stock_remaining_days": 1,
                "confidence": 0.5,
            }
        }))

    def test_still_have_reduces_consumption(self):
        ct.apply_feedback("Leite", "still_have")
        model = json.loads(self.model_file.read_text())
        assert model["leite"]["avg_weekly_consumption"]["value"] < 6.0

    def test_already_finished_increases_consumption(self):
        ct.apply_feedback("Leite", "already_finished")
        model = json.loads(self.model_file.read_text())
        assert model["leite"]["avg_weekly_consumption"]["value"] > 6.0

    def test_inactive_deactivates_product(self):
        ct.apply_feedback("Leite", "inactive")
        model = json.loads(self.model_file.read_text())
        assert model["leite"]["active"] is False

    def test_returns_error_for_unknown_product(self):
        result = ct.apply_feedback("Produto Inexistente", "still_have")
        assert "error" in result
