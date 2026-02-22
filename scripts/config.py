"""
Configuração central de integrações de mercado.

Este é o único ficheiro a editar quando se adiciona suporte a um novo supermercado online.
Todos os outros módulos (price_cache, price_compare, list_optimizer) importam daqui.

Para adicionar um novo supermercado:
  1. Adicionar entrada ao enum OnlineMarket abaixo
  2. Adicionar entrada ao DELIVERY_CONFIG abaixo
  3. Criar references/NOME_guide.md (navegação via browser tool, sem CSS selectors)
  4. Adicionar credenciais ao SKILL.md → metadata.openclaw.requires.env
  5. Adicionar testes em tests/test_price_compare.py para o novo mercado
  6. Atualizar README.md e CHANGELOG.md
"""

from enum import Enum


class OnlineMarket(str, Enum):
    """Mercados com integração online activa.

    Usar str como mixin permite usar os valores directamente como strings,
    mantendo compatibilidade com código que espera strings (argparse choices,
    chaves de dicionário, comparações com preferred_store, etc.).

    Exemplo:
        OnlineMarket.CONTINENTE == "continente"  # True
        "continente" in ONLINE_MARKET_IDS        # True
    """
    CONTINENTE = "continente"
    PINGODOCE = "pingodoce"


# Conjunto de IDs de mercados online — para lookups O(1).
# Usado por list_optimizer para distinguir preferência online de loja presencial:
#   preferred_store in ONLINE_MARKET_IDS  → preferência online (fica no fluxo normal)
#   preferred_store not in ONLINE_MARKET_IDS → loja presencial (vai para physical_items)
ONLINE_MARKET_IDS: frozenset[str] = frozenset(m.value for m in OnlineMarket)

# Lista ordenada de mercados — para iteração e argparse choices.
# A ordem determina o tie-break quando dois mercados têm o mesmo preço.
MARKETS: list[str] = [m.value for m in OnlineMarket]

# TTL da cache de preços (horas). Partilhado por price_cache.py e price_compare.py.
CACHE_TTL_HOURS: int = 24

# Configuração de entrega por mercado.
# Chaves são strings (valores do enum) para compatibilidade com código legado.
# Verificar os valores actuais nos sites antes de cada campanha.
DELIVERY_CONFIG: dict[str, dict[str, float]] = {
    OnlineMarket.CONTINENTE.value: {
        "cost": 3.99,
        "free_threshold": 50.0,
        "min_order": 0.0,
    },
    OnlineMarket.PINGODOCE.value: {
        "cost": 2.99,
        "free_threshold": 100.0,
        "min_order": 0.0,
    },
}
