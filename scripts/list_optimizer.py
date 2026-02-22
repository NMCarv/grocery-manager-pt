#!/usr/bin/env python3
"""
Gerador de lista de compras otimizada.
Combina itens manuais da família com previsões do modelo de consumo.

Usage:
  python3 list_optimizer.py weekly
  python3 list_optimizer.py bulk
  python3 list_optimizer.py triage --next-bulk-date 2026-03-01
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"
BUFFER_FACTOR = 1.15  # 15% extra para segurança
BULK_WEEKS = 4.5  # Compra a granel cobre ~4.5 semanas


def load_json(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or {}


def generate_weekly_list():
    """Gera lista de compra semanal baseada em modelo + itens manuais."""
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
    """Gera lista de compra a granel mensal."""
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


def generate_triage(next_bulk_date=None):
    """Triagem completa: combina weekly + separa itens para granel."""
    weekly = generate_weekly_list()
    
    if next_bulk_date:
        next_bulk = datetime.fromisoformat(next_bulk_date)
        days_to_bulk = (next_bulk - datetime.now(timezone.utc)).days
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
        "next_bulk_date": next_bulk_date,
        "days_to_bulk": days_to_bulk,
        "total_weekly": len(weekly_items),
        "total_bulk": len(bulk_items),
    }


def main():
    parser = argparse.ArgumentParser(description="List Optimizer")
    sub = parser.add_subparsers(dest="command")
    
    sub.add_parser("weekly")
    sub.add_parser("bulk")
    
    triage_p = sub.add_parser("triage")
    triage_p.add_argument("--next-bulk-date", help="ISO date da próxima compra a granel")
    
    args = parser.parse_args()
    
    if args.command == "weekly":
        result = generate_weekly_list()
    elif args.command == "bulk":
        result = generate_bulk_list()
    elif args.command == "triage":
        result = generate_triage(getattr(args, "next_bulk_date", None))
    else:
        parser.print_help()
        sys.exit(1)
        return
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
