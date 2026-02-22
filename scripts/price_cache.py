#!/usr/bin/env python3
"""
Gestão de cache de preços de supermercados.

O agente usa a browser tool do OpenClaw para extrair preços dos sites,
e depois chama este script para persistir/consultar os dados em cache.

Usage:
  python3 price_cache.py update --market continente --product "leite mimosa" --data '{"price": 1.29, ...}'
  python3 price_cache.py search --product "leite" [--market continente]
  python3 price_cache.py get --market continente --product "leite mimosa"
  python3 price_cache.py parse-price "2,49 €"
  python3 price_cache.py expired [--market continente]
  python3 price_cache.py stats
"""

import json
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "price_cache.json"
CACHE_TTL_HOURS = 24
MARKETS = ["continente", "pingodoce"]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {m: {} for m in MARKETS}


def save_cache(cache: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Core utilities
# ---------------------------------------------------------------------------

def normalize_key(name: str) -> str:
    """Normaliza nome de produto para uso como chave de cache."""
    return name.lower().strip()


def parse_price_pt(price_str: str) -> float | None:
    """
    Converte preço em formato PT para float.
    Exemplos: "2,49 €" → 2.49 | "1.299,00 €" → 1299.00 | "0,99" → 0.99
    """
    if not price_str:
        return None
    # Remover símbolo de moeda e espaços
    cleaned = price_str.strip().replace("€", "").strip()
    # Se tem ponto como separador de milhar e vírgula como decimal (formato PT)
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    # Remover qualquer caractere não numérico restante exceto ponto
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return None


def is_cache_valid(entry: dict) -> bool:
    """Verifica se uma entrada de cache ainda é válida (<24h)."""
    cached_at = entry.get("cached_at")
    if not cached_at:
        return False
    age_hours = (
        datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)
    ).total_seconds() / 3600
    return age_hours < CACHE_TTL_HOURS


def fuzzy_search(cache: dict, market: str, query: str, limit: int = 5) -> list[dict]:
    """
    Pesquisa produtos no cache por nome (substring match).
    Retorna lista ordenada por relevância.
    """
    query_lower = query.lower()
    market_cache = cache.get(market, {})
    results = []

    for key, entry in market_cache.items():
        if query_lower in key:
            score = 1.0 if key == query_lower else 0.5 + (len(query_lower) / len(key)) * 0.5
            results.append({**entry, "_key": key, "_score": score, "_market": market})

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:limit]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_update(args) -> dict:
    """Adiciona ou atualiza entrada de preço no cache."""
    cache = load_cache()
    market = args.market.lower()
    if market not in MARKETS:
        return {"error": f"Mercado desconhecido: {market}. Use: {MARKETS}"}

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        return {"error": f"JSON inválido em --data: {e}"}

    if not isinstance(data, dict):
        return {"error": f"--data deve ser um objeto JSON, recebido: {type(data).__name__}"}

    key = normalize_key(args.product)
    now = datetime.now(timezone.utc).isoformat()

    entry = {
        "name": args.product,
        "price": data.get("price"),
        "price_per_unit": data.get("price_per_unit"),
        "unit": data.get("unit", "un"),
        "brand": data.get("brand"),
        "promo": data.get("promo"),
        "promo_effective_price": data.get("promo_effective_price"),
        "available": data.get("available", True),
        "product_url": data.get("product_url"),
        "cached_at": now,
    }

    if market not in cache:
        cache[market] = {}
    cache[market][key] = entry
    save_cache(cache)
    return {"updated": key, "market": market, "price": entry["price"]}


def cmd_get(args) -> dict:
    """Obtém entrada de cache para um produto/mercado específico."""
    cache = load_cache()
    market = args.market.lower()
    key = normalize_key(args.product)
    entry = cache.get(market, {}).get(key)
    if not entry:
        return {"found": False, "key": key, "market": market}
    return {
        "found": True,
        "valid": is_cache_valid(entry),
        "market": market,
        **entry,
    }


def cmd_search(args) -> list:
    """Pesquisa produtos no cache."""
    cache = load_cache()
    markets_to_search = [args.market.lower()] if args.market else MARKETS
    results = []
    for market in markets_to_search:
        if market not in MARKETS:
            continue
        results.extend(fuzzy_search(cache, market, args.product))
    return results


def cmd_parse_price(args) -> dict:
    """Converte string de preço PT para float."""
    value = parse_price_pt(args.price_str)
    return {"input": args.price_str, "value": value}


def cmd_expired(args) -> dict:
    """Lista produtos com cache expirado."""
    cache = load_cache()
    markets_to_check = [args.market.lower()] if args.market else MARKETS
    expired = []
    for market in markets_to_check:
        for key, entry in cache.get(market, {}).items():
            if not is_cache_valid(entry):
                expired.append({"market": market, "product": key, "cached_at": entry.get("cached_at")})
    return {"expired_count": len(expired), "expired": expired}


def cmd_stats(args) -> dict:
    """Estatísticas do cache."""
    cache = load_cache()
    stats = {}
    total_valid = 0
    total_expired = 0
    for market in MARKETS:
        entries = cache.get(market, {})
        valid = sum(1 for e in entries.values() if is_cache_valid(e))
        expired = len(entries) - valid
        total_valid += valid
        total_expired += expired
        stats[market] = {"total": len(entries), "valid": valid, "expired": expired}
    stats["total"] = {"valid": total_valid, "expired": total_expired}
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Gestão de cache de preços")
    sub = parser.add_subparsers(dest="command")

    # update
    p_update = sub.add_parser("update", help="Adicionar/atualizar preço no cache")
    p_update.add_argument("--market", required=True, choices=MARKETS)
    p_update.add_argument("--product", required=True)
    p_update.add_argument("--data", required=True, help='JSON com campos: price, unit, brand, promo, available, ...')

    # get
    p_get = sub.add_parser("get", help="Obter preço de um produto")
    p_get.add_argument("--market", required=True, choices=MARKETS)
    p_get.add_argument("--product", required=True)

    # search
    p_search = sub.add_parser("search", help="Pesquisar produtos no cache")
    p_search.add_argument("--product", required=True)
    p_search.add_argument("--market", choices=MARKETS, default=None)

    # parse-price
    p_parse = sub.add_parser("parse-price", help="Converter preço PT para float")
    p_parse.add_argument("price_str")

    # expired
    p_expired = sub.add_parser("expired", help="Listar entradas expiradas")
    p_expired.add_argument("--market", choices=MARKETS, default=None)

    # stats
    sub.add_parser("stats", help="Estatísticas do cache")

    args = parser.parse_args()

    if args.command == "update":
        result = cmd_update(args)
    elif args.command == "get":
        result = cmd_get(args)
    elif args.command == "search":
        result = cmd_search(args)
    elif args.command == "parse-price":
        result = cmd_parse_price(args)
    elif args.command == "expired":
        result = cmd_expired(args)
    elif args.command == "stats":
        result = cmd_stats(args)
    else:
        parser.print_help()
        sys.exit(1)
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
