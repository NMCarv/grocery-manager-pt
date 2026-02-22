# Algoritmo de Comparação de Preços Multi-Mercado

## Objetivo

Dada uma lista de N itens com quantidades, encontrar a distribuição ótima pelos M supermercados
que minimize o custo total (incluindo entrega, cupões e saldo).

## Inputs

```
items[]:
  - name: str
  - quantity: float
  - unit: str (kg, L, un)
  - preferred_brand: str | null
  - acceptable_brands: str[]

markets[]:
  - id: str (continente, pingodoce)
  - delivery_cost: float
  - free_delivery_threshold: float | null
  - min_order: float | null
  - coupons[]: { description, discount_eur, min_spend, categories[] }
  - balance: float (saldo/pontos convertidos em €)
```

## Processo

### Passo 1 — Recolha de Preços

Para cada item × mercado:
1. Verificar `data/price_cache.json` — se preço tem <24h, usar cache
2. Se cache expirado → executar scraper do mercado correspondente
3. Registar para cada match:
   - `price_total`: preço do produto × quantidade
   - `price_per_unit`: preço normalizado (€/kg, €/L, €/un)
   - `brand`: marca do produto encontrado
   - `promo`: promoção ativa (se existir)
   - `promo_effective_price`: preço efetivo após promoção
   - `available`: bool

### Passo 2 — Normalização

- Converter todos os preços para a mesma base (€/kg, €/L, €/un)
- Para promoções tipo "leve 3 pague 2": calcular preço efetivo por unidade
- Para promoções tipo "50% na 2ª unidade": calcular preço efetivo considerando quantidade pedida
- Penalizar (soft) marcas não-preferidas: se não é preferred_brand, registar mas não descarta

### Passo 3 — Otimização

#### Abordagem: Greedy com ajuste

1. **Atribuição inicial:** Para cada item, atribuir ao mercado com menor preço efetivo
2. **Calcular subtotais** por mercado (soma dos itens atribuídos)
3. **Aplicar custos de entrega:**
   - Se subtotal ≥ free_delivery_threshold → entrega grátis
   - Senão → adicionar delivery_cost
4. **Aplicar cupões:** Para cada cupão do mercado, verificar se condições são cumpridas
5. **Aplicar saldo:** Subtrair saldo disponível do total do mercado
6. **Calcular total real** = Σ(subtotal_mercado + entrega - cupões - saldo)

#### Ajuste de threshold de entrega

Se um mercado está perto do threshold de entrega grátis (falta <€5):
- Tentar mover 1-2 itens do outro mercado para este
- Se o custo de mover os itens < custo da entrega → mover
- Recalcular

#### Simplificação

Se diferença entre usar 1 mercado vs 2 mercados < €5:
- Recomendar 1 mercado (menos entregas, menos complicação)
- Mostrar ambas as opções ao utilizador

### Passo 4 — Output

```json
{
  "recommendation": {
    "total_cost": 83.10,
    "savings_vs_single_store": 12.40,
    "markets": [
      {
        "id": "continente",
        "items": [...],
        "subtotal": 67.30,
        "delivery": 0.00,
        "coupons_applied": [{"desc": "3€ desc >50€", "value": 3.00}],
        "balance_used": 0.00,
        "total": 64.30
      },
      {
        "id": "pingodoce",
        "items": [...],
        "subtotal": 18.80,
        "delivery": 2.99,
        "coupons_applied": [],
        "balance_used": 2.30,
        "total": 19.49
      }
    ]
  },
  "alternatives": [
    {"strategy": "all_continente", "total": 89.20},
    {"strategy": "all_pingodoce", "total": 92.40}
  ]
}
```

## Heurísticas

- **Frescos:** Preferir um só mercado (qualidade inconsistente entre lojas)
- **Granel:** Nem sempre mais barato online — comparar com unidade normal
- **Promoções "talão":** Promoções que aparecem no talão de compra anterior — verificar na conta
- **Limites de quantidade:** Alguns supermercados limitam compras de promoção (max 3 unidades)
- **Peso variável:** Carne/peixe pode ter preço "desde X€/kg" — assumir peso médio
