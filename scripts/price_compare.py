#!/usr/bin/env python3
"""
Motor de comparação de preços multi-mercado.
Recebe lista de compras, consulta preços em cada mercado, e retorna
a distribuição ótima que minimiza custo total.

Usage:
  python3 price_compare.py --input data/inventory.json --output comparison.json

Lê: data/inventory.json (shopping_list), data/price_cache.json, data/family_preferences.json
Escreve: resultado da comparação (stdout JSON ou ficheiro)
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent.parent / "data"

MARKETS = ["continente", "pingodoce"]

# Custos de entrega default (atualizar com valores reais)
DELIVERY_CONFIG = {
    "continente": {
        "cost": 0.00,  # Geralmente grátis acima de 50€
        "free_threshold": 50.0,
        "min_order": 0.0,
    },
    "pingodoce": {
        "cost": 2.99,
        "free_threshold": 100.0,  # Verificar valor real
        "min_order": 0.0,
    },
}

SIMPLICITY_THRESHOLD = 5.0  # Se diff < 5€, preferir 1 mercado


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_shopping_list():
    inventory = load_json(DATA_DIR / "inventory.json")
    return inventory.get("shopping_list", [])


def load_price_cache():
    cache_path = DATA_DIR / "price_cache.json"
    if cache_path.exists():
        return load_json(cache_path)
    return {"continente": {}, "pingodoce": {}}


def load_preferences():
    prefs_path = DATA_DIR / "family_preferences.json"
    if prefs_path.exists():
        return load_json(prefs_path)
    return {}


def get_cached_price(cache, market, product_name):
    """Busca preço no cache. Retorna None se não existe ou expirado."""
    market_cache = cache.get(market, {})
    entry = market_cache.get(product_name.lower())
    if not entry:
        return None
    # Verificar TTL (24h)
    cached_at = entry.get("cached_at")
    if cached_at:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)).total_seconds()
        if age > 86400:
            return None
    return entry


def calculate_delivery(market, subtotal):
    """Calcula custo de entrega para um mercado dado o subtotal."""
    config = DELIVERY_CONFIG.get(market, {})
    threshold = config.get("free_threshold")
    if threshold and subtotal >= threshold:
        return 0.0
    return config.get("cost", 0.0)


def optimize_split(items_with_prices):
    """
    Algoritmo greedy com ajuste para encontrar split ótimo.
    
    Input: lista de {item, prices: {market: price_info}}
    Output: {markets: {market_id: {items, subtotal, delivery, total}}, total, savings}
    """
    # Passo 1: Atribuição greedy — cada item vai para o mercado mais barato
    assignments = {m: [] for m in MARKETS}
    
    for item_data in items_with_prices:
        item = item_data["item"]
        prices = item_data["prices"]
        
        best_market = None
        best_price = float("inf")
        
        for market, price_info in prices.items():
            if price_info and price_info.get("available", True):
                effective = price_info.get("promo_effective_price") or price_info.get("price", float("inf"))
                if effective < best_price:
                    best_price = effective
                    best_market = market
        
        if best_market:
            assignments[best_market].append({
                "item": item,
                "price": best_price,
                "price_info": prices.get(best_market, {}),
            })
        else:
            # Produto não encontrado em nenhum mercado
            assignments.setdefault("unavailable", []).append(item)
    
    # Passo 2: Calcular totais por mercado
    result = {"markets": {}, "total": 0, "unavailable": assignments.get("unavailable", [])}
    
    for market in MARKETS:
        items = assignments[market]
        if not items:
            continue
        
        subtotal = sum(i["price"] for i in items)
        delivery = calculate_delivery(market, subtotal)
        
        result["markets"][market] = {
            "items": [{"name": i["item"]["name"], "price": i["price"], "qty": i["item"].get("quantity", {}).get("value", 1)} for i in items],
            "subtotal": round(subtotal, 2),
            "delivery": round(delivery, 2),
            "coupons_applied": [],  # TODO: aplicar cupões
            "balance_used": 0.0,    # TODO: aplicar saldo
            "total": round(subtotal + delivery, 2),
        }
        result["total"] += subtotal + delivery
    
    result["total"] = round(result["total"], 2)
    
    # Passo 3: Ajuste de threshold de entrega
    for market in MARKETS:
        if market not in result["markets"]:
            continue
        m = result["markets"][market]
        config = DELIVERY_CONFIG.get(market, {})
        threshold = config.get("free_threshold")
        if threshold and m["subtotal"] < threshold:
            gap = threshold - m["subtotal"]
            if gap < 5.0 and m["delivery"] > 0:
                # Perto do threshold — vale a pena tentar puxar itens de outro mercado
                pass  # TODO: implementar lógica de rebalanceamento
    
    # Passo 4: Calcular alternativas single-store
    result["alternatives"] = []
    for market in MARKETS:
        alt_total = 0
        alt_available = True
        for item_data in items_with_prices:
            price_info = item_data["prices"].get(market)
            if price_info and price_info.get("available", True):
                alt_total += price_info.get("promo_effective_price") or price_info.get("price", 0)
            else:
                alt_available = False
        alt_delivery = calculate_delivery(market, alt_total)
        result["alternatives"].append({
            "strategy": f"all_{market}",
            "total": round(alt_total + alt_delivery, 2),
            "all_available": alt_available,
        })
    
    # Passo 5: Verificar se vale a pena split vs single
    best_single = min(result["alternatives"], key=lambda a: a["total"])
    if result["total"] > 0 and best_single["total"] - result["total"] < SIMPLICITY_THRESHOLD:
        result["recommendation_note"] = f"Diferença < €{SIMPLICITY_THRESHOLD}. Considerar tudo em {best_single['strategy']} por simplicidade."
    
    result["savings_vs_best_single"] = round(best_single["total"] - result["total"], 2)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Comparação de preços multi-mercado")
    parser.add_argument("--output", "-o", help="Ficheiro de output (default: stdout)")
    args = parser.parse_args()
    
    shopping_list = load_shopping_list()
    cache = load_price_cache()
    prefs = load_preferences()
    
    if not shopping_list:
        print(json.dumps({"error": "Lista de compras vazia"}))
        sys.exit(0)
    
    # Recolher preços (do cache por agora; scraping real requer browser)
    items_with_prices = []
    for item in shopping_list:
        prices = {}
        for market in MARKETS:
            cached = get_cached_price(cache, market, item["name"])
            if cached:
                prices[market] = cached
        items_with_prices.append({"item": item, "prices": prices})
    
    # Otimizar
    result = optimize_split(items_with_prices)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["items_count"] = len(shopping_list)
    
    output = json.dumps(result, indent=2, ensure_ascii=False)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Resultado gravado em {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
