#!/usr/bin/env python3
"""
Gerador de lista de compras otimizada.
Combina itens manuais da família com previsões do modelo de consumo.

Itens com preferred_store != null são excluídos das listas online e aparecem
em generate_physical_list(), agrupados por loja para visita presencial.

Usage:
  python3 list_optimizer.py weekly
  python3 list_optimizer.py bulk
  python3 list_optimizer.py triage --next-bulk-date 2026-03-01
  python3 list_optimizer.py physical
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

from config import ONLINE_MARKET_IDS

DATA_DIR = Path(__file__).parent.parent / "data"
BUFFER_FACTOR = 1.15  # 15% extra para segurança
BULK_WEEKS = 4.5  # Compra a granel cobre ~4.5 semanas


def load_json(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or {}


def generate_weekly_list():
    """Gera lista de compra semanal baseada em modelo + itens manuais.

    Produtos com preferred_store que NÃO seja um mercado online (ONLINE_MARKET_IDS)
    são considerados presenciais e excluídos — aparecem em generate_physical_list().

    Produtos com preferred_store que seja um mercado online (ex: "continente")
    são incluídos normalmente, e o campo preferred_store é propagado para que
    price_compare.py o possa honrar.
    """
    inventory = load_json(DATA_DIR / "inventory.json", {"shopping_list": []})
    model = load_json(DATA_DIR / "consumption_model.json", {})
    prefs = load_json(DATA_DIR / "family_preferences.json", {})

    manual_items = inventory.get("shopping_list", [])
    predicted_items = []

    # Previsões do modelo: produtos que devem acabar nos próximos 9 dias
    for product_id, entry in model.items():
        if not entry.get("active", True):
            continue
        if entry.get("confidence", 0) < 0.5:
            continue
        # Presencial = tem preferred_store definido e não é um mercado com integração online
        preferred_store = entry.get("preferred_store")
        if preferred_store and preferred_store not in ONLINE_MARKET_IDS:
            continue

        days_left = entry.get("estimated_stock_remaining_days", float("inf"))
        if days_left <= 9:  # Cobre até próxima triagem + buffer
            avg_weekly = entry.get("avg_weekly_consumption", {})
            if avg_weekly:
                quantity = round(avg_weekly["value"] * BUFFER_FACTOR, 1)
                predicted_items.append({
                    "name": entry["name"],
                    "category": entry.get("category", "outros"),
                    "quantity": {"value": quantity, "unit": avg_weekly.get("unit", "un")},
                    "source": "prediction",
                    "confidence": entry.get("confidence", 0),
                    "preferred_brand": entry.get("preferred_brand"),
                    "preferred_store": preferred_store,  # None ou mercado online (ex: "continente")
                    "days_left": days_left,
                    "bulk_eligible": entry.get("bulk_eligible", False),
                })

    # Merge: manual items têm prioridade
    manual_names = {i["name"].lower() for i in manual_items}

    combined = []
    for item in manual_items:
        item["source"] = "manual"
        combined.append(item)

    for item in predicted_items:
        if item["name"].lower() not in manual_names:
            combined.append(item)

    # Separar por categoria
    categorized = {}
    for item in combined:
        cat = item.get("category", "outros")
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(item)

    # Budget check
    budget = prefs.get("budget", {}).get("weekly_limit_eur", 150)

    return {
        "type": "weekly",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": combined,
        "categorized": categorized,
        "total_items": len(combined),
        "manual_items": len(manual_items),
        "predicted_items": len(predicted_items),
        "budget_limit": budget,
    }


def generate_bulk_list():
    """Gera lista de compra a granel mensal.

    Produtos com preferred_store que NÃO seja um mercado online são considerados
    presenciais e excluídos. Produtos com preferred_store de mercado online
    são incluídos normalmente.
    """
    model = load_json(DATA_DIR / "consumption_model.json", {})
    prefs = load_json(DATA_DIR / "family_preferences.json", {})

    bulk_items = []

    for product_id, entry in model.items():
        if not entry.get("active", True):
            continue
        if not entry.get("bulk_eligible", False):
            continue
        if entry.get("confidence", 0) < 0.5:
            continue
        # Presencial = tem preferred_store definido e não é um mercado com integração online
        preferred_store = entry.get("preferred_store")
        if preferred_store and preferred_store not in ONLINE_MARKET_IDS:
            continue

        avg_weekly = entry.get("avg_weekly_consumption", {})
        if avg_weekly:
            # Quantidade para ~4.5 semanas
            quantity = round(avg_weekly["value"] * BULK_WEEKS, 1)
            bulk_qty = entry.get("bulk_quantity")
            if bulk_qty:
                quantity = bulk_qty["value"]  # Usar quantidade bulk definida

            bulk_items.append({
                "name": entry["name"],
                "category": entry.get("category", "outros"),
                "quantity": {"value": quantity, "unit": avg_weekly.get("unit", "un")},
                "preferred_brand": entry.get("preferred_brand"),
                "source": "bulk_prediction",
            })

    budget = prefs.get("budget", {}).get("bulk_monthly_budget_eur", 120)

    return {
        "type": "bulk",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": bulk_items,
        "total_items": len(bulk_items),
        "budget_limit": budget,
    }


def generate_physical_list():
    """Gera lista de compras presenciais agrupada por loja física.

    Inclui todos os produtos com preferred_store que NÃO seja um mercado online
    (não está em ONLINE_MARKET_IDS). A distinção é feita via config.py — não é
    necessário definir physical_stores em family_preferences para o routing.

    O family_preferences.physical_stores serve apenas para metadados de exibição
    (nome da loja, frequência de visita, notas).

    Marca como urgente os que têm stock a acabar nos próximos 9 dias.
    Nunca executa compra online — serve apenas como lembrete de visita presencial.
    """
    model = load_json(DATA_DIR / "consumption_model.json", {})
    prefs = load_json(DATA_DIR / "family_preferences.json", {})

    physical_stores_config = prefs.get("physical_stores", {})
    stores = {}

    for product_id, entry in model.items():
        if not entry.get("active", True):
            continue
        if entry.get("confidence", 0) < 0.5:
            continue

        preferred_store = entry.get("preferred_store")
        # Presencial = tem preferred_store definido e NÃO está em ONLINE_MARKET_IDS
        if not preferred_store or preferred_store in ONLINE_MARKET_IDS:
            continue

        days_left = entry.get("estimated_stock_remaining_days", float("inf"))
        avg_weekly = entry.get("avg_weekly_consumption", {})

        if not avg_weekly:
            continue

        # Quantidade: usar bulk_quantity se for granel, caso contrário semanal + buffer
        bulk_qty = entry.get("bulk_quantity")
        if entry.get("bulk_eligible") and bulk_qty:
            quantity = bulk_qty["value"]
            unit = bulk_qty.get("unit", avg_weekly.get("unit", "un"))
        else:
            quantity = round(avg_weekly["value"] * BUFFER_FACTOR, 1)
            unit = avg_weekly.get("unit", "un")

        item = {
            "name": entry["name"],
            "category": entry.get("category", "outros"),
            "quantity": {"value": quantity, "unit": unit},
            "preferred_brand": entry.get("preferred_brand"),
            "days_left": days_left,
            "urgent": days_left <= 9,
            "bulk_eligible": entry.get("bulk_eligible", False),
            "source": "physical_prediction",
        }

        if preferred_store not in stores:
            store_cfg = physical_stores_config.get(preferred_store, {})

            stores[preferred_store] = {
                "store_id": preferred_store,
                "name": store_cfg.get("name", preferred_store.title()),
                "visit_frequency": store_cfg.get("visit_frequency"),
                "notes": store_cfg.get("notes"),
                "items": [],
                "urgent_count": 0,
            }

        stores[preferred_store]["items"].append(item)
        if item["urgent"]:
            stores[preferred_store]["urgent_count"] += 1

    return {
        "type": "physical",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stores": stores,
        "total_stores": len(stores),
        "total_items": sum(len(s["items"]) for s in stores.values()),
    }


def generate_triage(next_bulk_date=None):
    """Triagem completa: combina weekly + separa itens para granel + lista presencial."""
    weekly = generate_weekly_list()
    physical = generate_physical_list()

    if next_bulk_date:
        # Usar datetime naive para evitar erros de timezone com dates simples (YYYY-MM-DD)
        next_bulk = datetime.fromisoformat(next_bulk_date)
        days_to_bulk = (next_bulk - datetime.now()).days
    else:
        days_to_bulk = 30  # Assume 1 mês

    weekly_items = []
    bulk_items = []

    for item in weekly["items"]:
        if item.get("bulk_eligible", False) and days_to_bulk <= 7:
            bulk_items.append(item)
        else:
            weekly_items.append(item)

    return {
        "type": "triage",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "weekly_items": weekly_items,
        "bulk_items": bulk_items,
        "physical_items": physical["stores"],
        "next_bulk_date": next_bulk_date,
        "days_to_bulk": days_to_bulk,
        "total_weekly": len(weekly_items),
        "total_bulk": len(bulk_items),
        "total_physical": physical["total_items"],
    }


def main():
    parser = argparse.ArgumentParser(description="List Optimizer")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("weekly")
    sub.add_parser("bulk")
    sub.add_parser("physical")

    triage_p = sub.add_parser("triage")
    triage_p.add_argument("--next-bulk-date", help="ISO date da próxima compra a granel")

    args = parser.parse_args()

    if args.command == "weekly":
        result = generate_weekly_list()
    elif args.command == "bulk":
        result = generate_bulk_list()
    elif args.command == "physical":
        result = generate_physical_list()
    elif args.command == "triage":
        result = generate_triage(getattr(args, "next_bulk_date", None))
    else:
        parser.print_help()
        sys.exit(1)
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
