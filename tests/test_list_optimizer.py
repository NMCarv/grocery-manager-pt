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


def _prefs(weekly_limit=150, bulk_limit=120, next_bulk=None, physical_stores=None):
    return {
        "budget": {"weekly_limit_eur": weekly_limit, "bulk_monthly_budget_eur": bulk_limit},
        "next_bulk_date": next_bulk,
        "bulk_interval_days": 30,
        "physical_stores": physical_stores if physical_stores is not None else {
            "lidl": {"name": "Lidl", "visit_frequency": "semanal"},
            "makro": {"name": "Makro", "visit_frequency": "mensal"},
        },
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

    def test_triage_includes_physical_items(self):
        """Triagem inclui physical_items e total_physical no resultado."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 3,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            }
        }))
        result = lo.generate_triage()
        assert "physical_items" in result
        assert "total_physical" in result
        assert result["total_physical"] == 1
        # Item presencial não deve aparecer na lista semanal online
        assert result["total_weekly"] == 0

    def test_triage_physical_items_empty_when_no_physical_products(self):
        """Se não houver produtos presenciais, physical_items é dict vazio."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": None,
            }
        }))
        result = lo.generate_triage()
        assert result["physical_items"] == {}
        assert result["total_physical"] == 0


# ---------------------------------------------------------------------------
# generate_physical_list
# ---------------------------------------------------------------------------

class TestGeneratePhysicalList:
    @pytest.fixture(autouse=True)
    def patch_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lo, "DATA_DIR", tmp_path)
        self.tmp = tmp_path
        (self.tmp / "family_preferences.json").write_text(json.dumps(_prefs()))

    def _write_model(self, model):
        (self.tmp / "consumption_model.json").write_text(json.dumps(model))

    def _write_prefs(self, prefs):
        (self.tmp / "family_preferences.json").write_text(json.dumps(prefs))

    def test_empty_model_returns_no_stores(self):
        self._write_model({})
        result = lo.generate_physical_list()
        assert result["total_stores"] == 0
        assert result["total_items"] == 0
        assert result["stores"] == {}

    def test_online_only_items_not_included(self):
        """Produtos com preferred_store=None não aparecem na lista presencial."""
        self._write_model({
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": None,
            }
        })
        result = lo.generate_physical_list()
        assert result["total_items"] == 0

    def test_physical_item_grouped_by_store(self):
        """Produto com preferred_store aparece agrupado pela loja correta."""
        self._write_model({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 3,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            }
        })
        result = lo.generate_physical_list()
        assert result["total_stores"] == 1
        assert result["total_items"] == 1
        assert "lidl" in result["stores"]
        assert len(result["stores"]["lidl"]["items"]) == 1
        assert result["stores"]["lidl"]["items"][0]["name"] == "Café"

    def test_urgent_flag_when_stock_low(self):
        """Items com stock ≤ 9 dias são marcados como urgentes."""
        self._write_model({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 5,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            }
        })
        result = lo.generate_physical_list()
        item = result["stores"]["lidl"]["items"][0]
        assert item["urgent"] is True
        assert result["stores"]["lidl"]["urgent_count"] == 1

    def test_not_urgent_when_stock_ok(self):
        """Items com stock > 9 dias não são urgentes."""
        self._write_model({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 20,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            }
        })
        result = lo.generate_physical_list()
        item = result["stores"]["lidl"]["items"][0]
        assert item["urgent"] is False
        assert result["stores"]["lidl"]["urgent_count"] == 0

    def test_bulk_quantity_used_for_bulk_eligible(self):
        """Produtos bulk_eligible usam bulk_quantity em vez da quantidade semanal."""
        self._write_model({
            "arroz_makro": {
                "name": "Arroz Granel",
                "category": "conservas",
                "estimated_stock_remaining_days": 5,
                "avg_weekly_consumption": {"value": 2.0, "unit": "kg"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": True,
                "bulk_quantity": {"value": 25.0, "unit": "kg"},
                "preferred_store": "makro",
            }
        })
        result = lo.generate_physical_list()
        item = result["stores"]["makro"]["items"][0]
        assert item["quantity"]["value"] == 25.0
        assert item["quantity"]["unit"] == "kg"

    def test_multiple_stores_grouped_separately(self):
        """Produtos de lojas diferentes agrupam-se corretamente."""
        self._write_model({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 3,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            },
            "arroz_makro": {
                "name": "Arroz Granel",
                "category": "conservas",
                "estimated_stock_remaining_days": 5,
                "avg_weekly_consumption": {"value": 2.0, "unit": "kg"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": True,
                "bulk_quantity": {"value": 25.0, "unit": "kg"},
                "preferred_store": "makro",
            }
        })
        result = lo.generate_physical_list()
        assert result["total_stores"] == 2
        assert result["total_items"] == 2
        assert "lidl" in result["stores"]
        assert "makro" in result["stores"]

    def test_store_metadata_from_preferences(self):
        """Metadados da loja são lidos de family_preferences.json."""
        self._write_model({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 3,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            }
        })
        prefs = _prefs()
        prefs["physical_stores"] = {
            "lidl": {"name": "Lidl", "visit_frequency": "semanal", "notes": "Café aqui"}
        }
        self._write_prefs(prefs)
        result = lo.generate_physical_list()
        store = result["stores"]["lidl"]
        assert store["name"] == "Lidl"
        assert store["visit_frequency"] == "semanal"
        assert store["notes"] == "Café aqui"

    def test_inactive_items_excluded(self):
        """Produtos inativos não aparecem na lista presencial."""
        self._write_model({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 3,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": False,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            }
        })
        result = lo.generate_physical_list()
        assert result["total_items"] == 0

    def test_low_confidence_items_excluded(self):
        """Produtos com confidence < 0.5 não aparecem na lista presencial."""
        self._write_model({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 3,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.3,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",
            }
        })
        result = lo.generate_physical_list()
        assert result["total_items"] == 0


# ---------------------------------------------------------------------------
# Separação online vs presencial (integração)
# ---------------------------------------------------------------------------

class TestOnlineVsPhysicalSeparation:
    @pytest.fixture(autouse=True)
    def patch_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lo, "DATA_DIR", tmp_path)
        self.tmp = tmp_path
        (self.tmp / "inventory.json").write_text(json.dumps(_inventory()))
        (self.tmp / "family_preferences.json").write_text(json.dumps(_prefs()))

    def test_weekly_excludes_physical_store_items(self):
        """generate_weekly_list não inclui itens com preferred_store definido."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "leite": {
                "name": "Leite",
                "category": "lacticínios",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 6.0, "unit": "L"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": None,  # online
            },
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",  # presencial
            }
        }))
        result = lo.generate_weekly_list()
        names = [i["name"] for i in result["items"]]
        assert "Leite" in names
        assert "Café" not in names

    def test_bulk_excludes_physical_store_items(self):
        """generate_bulk_list não inclui itens com preferred_store de loja presencial."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "arroz": {
                "name": "Arroz",
                "category": "conservas",
                "avg_weekly_consumption": {"value": 2.0, "unit": "kg"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": True,
                "preferred_store": None,  # online
            },
            "arroz_makro": {
                "name": "Arroz Granel",
                "category": "conservas",
                "avg_weekly_consumption": {"value": 3.0, "unit": "kg"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": True,
                "bulk_quantity": {"value": 25.0, "unit": "kg"},
                "preferred_store": "makro",  # presencial (está em physical_stores)
            }
        }))
        result = lo.generate_bulk_list()
        names = [i["name"] for i in result["items"]]
        assert "Arroz" in names
        assert "Arroz Granel" not in names

    def test_online_preferred_store_not_excluded_from_weekly(self):
        """preferred_store='continente' é preferência online — item fica na lista semanal."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "continente",  # preferência online, não presencial
            }
        }))
        # 'continente' não está em physical_stores → item deve aparecer na lista online
        result = lo.generate_weekly_list()
        names = [i["name"] for i in result["items"]]
        assert "Café" in names

    def test_online_preferred_store_propagated_in_item(self):
        """preferred_store online é propagado no item para price_compare o honrar."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "continente",
            }
        }))
        result = lo.generate_weekly_list()
        item = next(i for i in result["items"] if i["name"] == "Café")
        assert item.get("preferred_store") == "continente"

    def test_physical_store_not_treated_as_online(self):
        """preferred_store='lidl' é presencial — item não deve aparecer na lista online."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "lidl",  # lidl está em physical_stores → presencial
            }
        }))
        result = lo.generate_weekly_list()
        names = [i["name"] for i in result["items"]]
        assert "Café" not in names

    def test_physical_list_excludes_online_preferred_store(self):
        """preferred_store='continente' não aparece na lista presencial."""
        (self.tmp / "consumption_model.json").write_text(json.dumps({
            "cafe": {
                "name": "Café",
                "category": "bebidas",
                "estimated_stock_remaining_days": 1,
                "avg_weekly_consumption": {"value": 250.0, "unit": "g"},
                "confidence": 0.8,
                "active": True,
                "bulk_eligible": False,
                "preferred_store": "continente",  # mercado online, não presencial
            }
        }))
        result = lo.generate_physical_list()
        assert result["total_items"] == 0
