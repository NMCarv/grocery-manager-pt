#!/usr/bin/env python3
"""
Motor de comparação de preços multi-mercado.
Recebe lista de compras, consulta preços em cache, e retorna
a distribuição ótima que minimiza custo total (incluindo entrega, cupões e saldo).

Usage:
  python3 price_compare.py [--output comparison.json]

Lê: data/inventory.json (shopping_list), data/price_cache.json, data/family_preferences.json
Escreve: resultado da comparação (stdout JSON ou ficheiro)
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

from config import MARKETS, ONLINE_MARKET_IDS, DELIVERY_CONFIG, CACHE_TTL_HOURS

DATA_DIR = Path(__file__).parent.parent / "data"

# Parâmetros de algoritmo (não dependem do mercado — permanecem aqui)
SIMPLICITY_THRESHOLD = 5.0   # Se diff < €5, preferir 1 mercado
DELIVERY_GAP_THRESHOLD = 5.0  # Tentar rebalancear se faltam <€5 para entrega grátis


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_json(path, default=None):
    p = Path(path)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return default if default is not None else {}


def load_shopping_list() -> list:
    inventory = load_json(DATA_DIR / "inventory.json", {"shopping_list": []})
    return inventory.get("shopping_list", [])


def load_price_cache() -> dict:
    cache = load_json(DATA_DIR / "price_cache.json", {m: {} for m in MARKETS})
    return cache


def load_preferences() -> dict:
    return load_json(DATA_DIR / "family_preferences.json", {})


# ---------------------------------------------------------------------------
# Cache lookup
# ---------------------------------------------------------------------------

def is_cache_valid(entry: dict) -> bool:
    cached_at = entry.get("cached_at")
    if not cached_at:
        return False
    age_hours = (
        datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)
    ).total_seconds() / 3600
    return age_hours < CACHE_TTL_HOURS


def get_cached_price(cache: dict, market: str, product_name: str) -> dict | None:
    """Retorna entrada de cache válida ou None."""
    key = product_name.lower().strip()
    entry = cache.get(market, {}).get(key)
    if entry and is_cache_valid(entry):
        return entry
    # Tentativa de match parcial (substring)
    for k, v in cache.get(market, {}).items():
        if key in k or k in key:
            if is_cache_valid(v):
                return v
    return None


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

def calculate_delivery(market: str, subtotal: float) -> float:
    config = DELIVERY_CONFIG.get(market, {})
    threshold = config.get("free_threshold")
    if threshold is not None and subtotal >= threshold:
        return 0.0
    return config.get("cost", 0.0)


def gap_to_free_delivery(market: str, subtotal: float) -> float:
    """Devolve quanto falta para entrega grátis (0 se já é grátis)."""
    config = DELIVERY_CONFIG.get(market, {})
    threshold = config.get("free_threshold")
    if threshold is None:
        return 0.0
    gap = threshold - subtotal
    return max(0.0, gap)


# ---------------------------------------------------------------------------
# Coupon logic
# ---------------------------------------------------------------------------

def apply_coupons(subtotal: float, coupons: list[dict], categories_in_cart: set[str]) -> tuple[float, list[dict]]:
    """
    Aplica cupões disponíveis a um subtotal.

    Cada cupão tem: description, discount_eur, min_spend, categories ([] = todos)
    Retorna: (desconto_total, lista_cupoes_aplicados)
    Greedy: aplica cupões por ordem de valor decrescente.
    """
    applicable = []
    for coupon in coupons:
        min_spend = coupon.get("min_spend", 0.0)
        allowed_cats = coupon.get("categories", [])
        if subtotal < min_spend:
            continue
        if allowed_cats and not categories_in_cart.intersection(allowed_cats):
            continue
        applicable.append(coupon)

    # Ordenar por desconto decrescente
    applicable.sort(key=lambda c: c.get("discount_eur", 0.0), reverse=True)

    total_discount = 0.0
    applied = []
    for coupon in applicable:
        discount = min(coupon.get("discount_eur", 0.0), subtotal - total_discount)
        if discount > 0:
            total_discount += discount
            applied.append({
                "description": coupon.get("description", ""),
                "discount_eur": round(discount, 2),
            })

    return round(total_discount, 2), applied


# ---------------------------------------------------------------------------
# Core optimization
# ---------------------------------------------------------------------------

def optimize_split(items_with_prices: list, market_config: dict | None = None) -> dict:
    """
    Algoritmo greedy com rebalanceamento para encontrar split ótimo.

    Input:
        items_with_prices: lista de {item, prices: {market: price_info}}
        market_config: config de cupões/saldo por mercado (opcional)
            {market: {coupons: [...], balance: float}}

    Output: {markets, total, savings_vs_best_single, alternatives, unavailable, recommendation_note}
    """
    if market_config is None:
        market_config = {m: {"coupons": [], "balance": 0.0} for m in MARKETS}

    # Passo 1: Atribuição greedy — cada item vai para o mercado com menor preço efetivo.
    # Se o item tiver preferred_store que seja um mercado online, tenta-se aí primeiro;
    # apenas se não estiver disponível é que se cai para o mercado mais barato.
    assignments = {m: [] for m in MARKETS}
    unavailable_items = []

    for item_data in items_with_prices:
        item = item_data["item"]
        prices = item_data["prices"]

        # Preferência de mercado online (ex: "continente" para produto específico da marca)
        item_preferred = item.get("preferred_store") if item.get("preferred_store") in ONLINE_MARKET_IDS else None

        # Tentar mercado preferido primeiro
        assigned = False
        if item_preferred:
            pref_info = prices.get(item_preferred)
            if pref_info and pref_info.get("available", True):
                pref_effective = pref_info.get("promo_effective_price") or pref_info.get("price")
                if pref_effective is not None:
                    assignments[item_preferred].append({
                        "item": item,
                        "price": pref_effective,
                        "price_info": pref_info,
                        "preferred_store_honored": True,
                    })
                    assigned = True

        if not assigned:
            # Greedy normal: mercado mais barato disponível
            best_market = None
            best_price = float("inf")

            for market in MARKETS:
                price_info = prices.get(market)
                if not price_info or not price_info.get("available", True):
                    continue
                effective = price_info.get("promo_effective_price") or price_info.get("price")
                if effective is None:
                    continue
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
                unavailable_items.append({
                    "name": item.get("name"),
                    "reason": "Não encontrado em nenhum mercado no cache",
                })

    # Passo 2: Calcular subtotais e categorias por mercado
    def build_market_result(market: str, items: list) -> dict | None:
        if not items:
            return None

        subtotal = sum(i["price"] for i in items)
        categories = {i["item"].get("category", "outros") for i in items}

        # Cupões
        coupons = market_config.get(market, {}).get("coupons", [])
        coupon_discount, applied_coupons = apply_coupons(subtotal, coupons, categories)

        # Saldo de cartão/pontos
        balance = market_config.get(market, {}).get("balance", 0.0)
        balance_used = min(balance, max(0.0, subtotal - coupon_discount))

        after_discounts = subtotal - coupon_discount - balance_used
        delivery = calculate_delivery(market, after_discounts)
        total = after_discounts + delivery

        return {
            "items": [
                {
                    "name": i["item"]["name"],
                    "qty": i["item"].get("quantity", {}).get("value", 1),
                    "unit": i["item"].get("quantity", {}).get("unit", "un"),
                    "price": round(i["price"], 2),
                    "brand": i["price_info"].get("brand"),
                    "promo": i["price_info"].get("promo"),
                }
                for i in items
            ],
            "subtotal": round(subtotal, 2),
            "coupon_discount": round(coupon_discount, 2),
            "coupons_applied": applied_coupons,
            "balance_used": round(balance_used, 2),
            "after_discounts": round(after_discounts, 2),
            "delivery": round(delivery, 2),
            "total": round(total, 2),
        }

    result_markets = {}
    for market in MARKETS:
        m_result = build_market_result(market, assignments[market])
        if m_result:
            result_markets[market] = m_result

    # Passo 3: Rebalanceamento de threshold de entrega
    # Se um mercado está perto do threshold de entrega grátis (falta <€5),
    # tentar mover itens baratos do outro mercado para atingir o threshold.
    for target_market in MARKETS:
        if target_market not in result_markets:
            continue
        m = result_markets[target_market]
        gap = gap_to_free_delivery(target_market, m["after_discounts"])
        if 0 < gap <= DELIVERY_GAP_THRESHOLD and m["delivery"] > 0:
            # Procurar itens candidatos no outro mercado para mover
            other_markets = [mk for mk in MARKETS if mk != target_market and mk in result_markets]
            for other_market in other_markets:
                other = result_markets[other_market]
                candidates = sorted(
                    assignments[other_market],
                    key=lambda x: x["price"],
                )
                moved = []
                gap_remaining = gap
                for candidate in candidates:
                    price_in_target = (
                        candidate["item_data"]["prices"].get(target_market, {}).get("price")
                        if "item_data" in candidate
                        else None
                    )
                    # Usar o preço do candidato no mercado alvo (se disponível)
                    move_price = price_in_target or candidate["price"]
                    if gap_remaining > 0:
                        moved.append(candidate)
                        gap_remaining -= move_price
                        if gap_remaining <= 0:
                            break

                if moved:
                    # Verificar se mover é vantajoso:
                    delivery_saved = m["delivery"]  # entrega que passaria a ser grátis
                    extra_cost = sum(
                        (mv.get("price_in_target", mv["price"]) - mv["price"])
                        for mv in moved
                    )
                    if delivery_saved > extra_cost:
                        # Aplicar rebalanceamento
                        for mv in moved:
                            assignments[other_market].remove(mv)
                            assignments[target_market].append(mv)
                        # Reconstruir resultados
                        m_new = build_market_result(target_market, assignments[target_market])
                        o_new = build_market_result(other_market, assignments[other_market])
                        if m_new:
                            result_markets[target_market] = m_new
                        if o_new:
                            result_markets[other_market] = o_new
                        elif other_market in result_markets:
                            del result_markets[other_market]

    # Passo 4: Total do split ótimo
    total_split = sum(m["total"] for m in result_markets.values())

    # Passo 5: Alternativas single-store
    alternatives = []
    for market in MARKETS:
        alt_subtotal = 0.0
        all_available = True
        for item_data in items_with_prices:
            price_info = item_data["prices"].get(market)
            if price_info and price_info.get("available", True):
                p = price_info.get("promo_effective_price") or price_info.get("price", 0.0)
                alt_subtotal += p or 0.0
            else:
                all_available = False

        # Aplicar cupões e saldo para single-store
        cats = {id["item"].get("category", "outros") for id in items_with_prices}
        coupons = market_config.get(market, {}).get("coupons", [])
        coupon_disc, _ = apply_coupons(alt_subtotal, coupons, cats)
        balance = market_config.get(market, {}).get("balance", 0.0)
        balance_used = min(balance, max(0.0, alt_subtotal - coupon_disc))
        after = alt_subtotal - coupon_disc - balance_used
        delivery = calculate_delivery(market, after)
        alt_total = after + delivery

        alternatives.append({
            "strategy": f"all_{market}",
            "subtotal": round(alt_subtotal, 2),
            "coupon_discount": round(coupon_disc, 2),
            "balance_used": round(balance_used, 2),
            "delivery": round(delivery, 2),
            "total": round(alt_total, 2),
            "all_available": all_available,
        })

    alternatives.sort(key=lambda a: a["total"])
    best_single = alternatives[0] if alternatives else None

    # Passo 6: Recomendação
    recommendation_note = None
    if best_single and total_split > 0:
        savings = round(best_single["total"] - total_split, 2)
        if savings < SIMPLICITY_THRESHOLD:
            recommendation_note = (
                f"Poupança do split é apenas €{savings:.2f} (< €{SIMPLICITY_THRESHOLD}). "
                f"Considerar tudo em {best_single['strategy'].replace('all_', '')} por simplicidade."
            )

    return {
        "markets": result_markets,
        "total": round(total_split, 2),
        "savings_vs_best_single": round((best_single["total"] - total_split) if best_single else 0, 2),
        "alternatives": alternatives,
        "unavailable": unavailable_items,
        "recommendation_note": recommendation_note,
    }


# ---------------------------------------------------------------------------
# Budget check
# ---------------------------------------------------------------------------

def check_budget(total: float, prefs: dict) -> dict:
    budget = prefs.get("budget", {})
    weekly_limit = budget.get("weekly_limit_eur", 150.0)
    over_budget = total > weekly_limit
    return {
        "total": total,
        "weekly_limit": weekly_limit,
        "over_budget": over_budget,
        "over_by": round(max(0, total - weekly_limit), 2),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Comparação de preços multi-mercado")
    parser.add_argument("--output", "-o", help="Ficheiro de output (default: stdout)")
    args = parser.parse_args()

    shopping_list = load_shopping_list()
    cache = load_price_cache()
    prefs = load_preferences()

    if not shopping_list:
        print(json.dumps({"error": "Lista de compras vazia"}, ensure_ascii=False))
        sys.exit(0)

    # Recolher preços do cache
    items_with_prices = []
    missing_from_cache = []
    for item in shopping_list:
        prices = {}
        for market in MARKETS:
            cached = get_cached_price(cache, market, item["name"])
            if cached:
                prices[market] = cached
        items_with_prices.append({"item": item, "prices": prices})
        if not prices:
            missing_from_cache.append(item["name"])

    # Otimizar
    result = optimize_split(items_with_prices)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["items_count"] = len(shopping_list)

    if missing_from_cache:
        result["missing_from_cache"] = missing_from_cache
        result["warning"] = (
            f"{len(missing_from_cache)} produto(s) não encontrado(s) no cache. "
            "Usar browser tool para pesquisar preços e atualizar cache antes de comparar."
        )

    # Verificar budget
    result["budget_check"] = check_budget(result["total"], prefs)

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Resultado gravado em {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
