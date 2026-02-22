#!/usr/bin/env python3
"""
Tracker de hábitos de consumo.
Atualiza o modelo de consumo após compras e gera alertas proativos.

Usage:
  python3 consumption_tracker.py update --purchase purchase_data.json
  python3 consumption_tracker.py check-stock
  python3 consumption_tracker.py predict --product "leite"
  python3 consumption_tracker.py feedback --product "leite" --type "still_have"
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_FILE = DATA_DIR / "consumption_model.json"
HISTORY_FILE = DATA_DIR / "shopping_history.json"

SEASONAL_FACTORS = {
    "gelados": {"6": 1.3, "7": 1.4, "8": 1.4, "9": 1.2},
    "sumos": {"6": 1.2, "7": 1.3, "8": 1.3, "9": 1.2},
    "sopas": {"11": 1.2, "12": 1.3, "1": 1.3, "2": 1.2},
    "chocolate": {"11": 1.2, "12": 1.4, "1": 1.2},
}

ALERT_THRESHOLD_DAYS = 2


def load_json(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_seasonal_factor(category):
    """Retorna fator sazonal para a categoria no mês atual."""
    month = str(datetime.now().month)
    factors = SEASONAL_FACTORS.get(category, {})
    return factors.get(month, 1.0)


def weighted_average(values, max_weight=4):
    """Média ponderada com peso decrescente (mais recente = mais relevante)."""
    if not values:
        return 0
    n = len(values)
    weights = [min(max_weight, n - i) for i in range(n)]
    total_weight = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def update_model_after_purchase(purchase_data):
    """Atualiza o modelo de consumo com dados de uma compra."""
    model = load_json(MODEL_FILE, {})
    
    for item in purchase_data.get("items", []):
        product_id = item.get("id") or item["name"].lower().replace(" ", "_")
        
        if product_id not in model:
            model[product_id] = {
                "name": item["name"],
                "category": item.get("category", "outros"),
                "purchase_history": [],
                "preferred_brand": item.get("brand"),
                "acceptable_brands": [item.get("brand")] if item.get("brand") else [],
                "bulk_eligible": False,
                "confidence": 0.0,
            }
        
        entry = model[product_id]
        
        # Adicionar ao histórico (manter últimos 12)
        entry["purchase_history"].append({
            "date": purchase_data.get("date", datetime.now(timezone.utc).isoformat()),
            "quantity": item.get("quantity", 1),
            "unit": item.get("unit", "un"),
            "market": purchase_data.get("market", "unknown"),
            "price": item.get("price", 0),
        })
        entry["purchase_history"] = entry["purchase_history"][-12:]
        
        # Recalcular médias
        history = entry["purchase_history"]
        if len(history) >= 2:
            intervals = []
            weekly_consumptions = []
            for i in range(1, len(history)):
                d1 = datetime.fromisoformat(history[i-1]["date"])
                d2 = datetime.fromisoformat(history[i]["date"])
                days = (d2 - d1).days
                if days > 0:
                    intervals.append(days)
                    weekly_consumptions.append(history[i-1]["quantity"] / days * 7)
            
            if intervals:
                entry["avg_purchase_interval_days"] = round(weighted_average(intervals), 1)
            if weekly_consumptions:
                entry["avg_weekly_consumption"] = {
                    "value": round(weighted_average(weekly_consumptions), 2),
                    "unit": history[-1].get("unit", "un"),
                }
        
        # Atualizar metadata
        entry["last_purchased"] = purchase_data.get("date", datetime.now(timezone.utc).isoformat())
        entry["last_quantity"] = item.get("quantity", 1)
        entry["confidence"] = min(1.0, len(history) / 8)
        
        # Recalcular stock estimado
        if entry.get("avg_weekly_consumption"):
            daily = entry["avg_weekly_consumption"]["value"] / 7
            if daily > 0:
                entry["estimated_stock_remaining_days"] = round(item.get("quantity", 1) / daily, 1)
    
    save_json(MODEL_FILE, model)
    return {"updated": len(purchase_data.get("items", [])), "model_size": len(model)}


def check_stock():
    """Verifica quais produtos estão próximos de acabar."""
    model = load_json(MODEL_FILE, {})
    alerts = []
    
    now = datetime.now(timezone.utc)
    
    for product_id, entry in model.items():
        if entry.get("confidence", 0) < 0.5:
            continue
        
        last_purchased = entry.get("last_purchased")
        if not last_purchased:
            continue
        
        avg_weekly = entry.get("avg_weekly_consumption", {}).get("value", 0)
        if avg_weekly <= 0:
            continue
        
        daily_consumption = avg_weekly / 7 * get_seasonal_factor(entry.get("category", ""))
        days_since = (now - datetime.fromisoformat(last_purchased)).days
        last_qty = entry.get("last_quantity", 0)
        
        remaining = last_qty - (daily_consumption * days_since)
        days_left = remaining / daily_consumption if daily_consumption > 0 else float("inf")
        
        entry["estimated_stock_remaining_days"] = round(max(0, days_left), 1)
        
        if days_left <= ALERT_THRESHOLD_DAYS:
            alerts.append({
                "product_id": product_id,
                "name": entry["name"],
                "days_left": round(days_left, 1),
                "category": entry.get("category", "outros"),
                "confidence": entry.get("confidence", 0),
            })
    
    save_json(MODEL_FILE, model)
    return {"alerts": alerts, "checked": len(model)}


def apply_feedback(product_name, feedback_type):
    """Ajusta modelo com base em feedback do utilizador."""
    model = load_json(MODEL_FILE, {})
    product_id = product_name.lower().replace(" ", "_")
    
    # Fuzzy match
    if product_id not in model:
        for pid in model:
            if product_name.lower() in model[pid]["name"].lower():
                product_id = pid
                break
    
    if product_id not in model:
        return {"error": f"Produto '{product_name}' não encontrado no modelo"}
    
    entry = model[product_id]
    
    if feedback_type == "still_have":
        # Produto durou mais que o previsto — aumentar duração
        if entry.get("avg_weekly_consumption"):
            entry["avg_weekly_consumption"]["value"] *= 0.8  # Reduzir consumo estimado em 20%
            entry["estimated_stock_remaining_days"] = max(3, entry.get("estimated_stock_remaining_days", 0) + 3)
    
    elif feedback_type == "already_finished":
        # Produto acabou mais cedo — diminuir duração
        if entry.get("avg_weekly_consumption"):
            entry["avg_weekly_consumption"]["value"] *= 1.2  # Aumentar consumo estimado em 20%
            entry["estimated_stock_remaining_days"] = 0
    
    elif feedback_type == "inactive":
        entry["active"] = False
    
    save_json(MODEL_FILE, model)
    return {"updated": product_id, "feedback": feedback_type}


def main():
    parser = argparse.ArgumentParser(description="Consumption Tracker")
    sub = parser.add_subparsers(dest="command")
    
    update_p = sub.add_parser("update")
    update_p.add_argument("--purchase", required=True, help="JSON file with purchase data")
    
    sub.add_parser("check-stock")
    
    predict_p = sub.add_parser("predict")
    predict_p.add_argument("--product", required=True)
    
    fb_p = sub.add_parser("feedback")
    fb_p.add_argument("--product", required=True)
    fb_p.add_argument("--type", required=True, choices=["still_have", "already_finished", "inactive"])
    
    args = parser.parse_args()
    
    if args.command == "update":
        data = json.loads(Path(args.purchase).read_text())
        result = update_model_after_purchase(data)
        print(json.dumps(result, indent=2))
    
    elif args.command == "check-stock":
        result = check_stock()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "feedback":
        result = apply_feedback(args.product, args.type)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
