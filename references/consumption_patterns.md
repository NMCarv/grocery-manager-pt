# Modelo de Padrões de Consumo

## Objetivo

Prever quando cada produto vai acabar e gerar listas de compras proativas.

## Estrutura do Modelo (`data/consumption_model.json`)

```json
{
  "product_id": {
    "name": "Nome do produto",
    "category": "categoria",
    "avg_weekly_consumption": { "value": 5.5, "unit": "L" },
    "avg_purchase_interval_days": 7,
    "preferred_brand": "Marca X",
    "acceptable_brands": ["Marca X", "Marca Y"],
    "purchase_history": [
      { "date": "2026-02-15", "quantity": 6, "unit": "L", "market": "continente", "price": 5.94 }
    ],
    "last_purchased": "2026-02-15",
    "estimated_stock_remaining_days": 3,
    "bulk_eligible": true,
    "bulk_quantity": { "value": 12, "unit": "L" },
    "seasonal_factors": { "summer": 1.2, "winter": 0.9 },
    "confidence": 0.85
  }
}
```

## Cálculos

### Consumo médio semanal
```
avg_weekly = média(quantity / days_between_purchases × 7) dos últimos 8 compras
```
Usar média ponderada com peso decrescente (mais recente = mais relevante):
- Última compra: peso 4
- Penúltima: peso 3
- Antepenúltima: peso 2
- Restantes: peso 1

### Stock restante estimado
```
days_since_purchase = today - last_purchased
daily_consumption = avg_weekly / 7
stock_at_purchase = last_quantity_bought
estimated_remaining = stock_at_purchase - (daily_consumption × days_since_purchase)
estimated_days_left = estimated_remaining / daily_consumption
```

### Fator sazonal
Ajustar consumo com multiplicador baseado no mês:
- Gelados, sumos, água: ↑ no verão (Jun-Set × 1.3)
- Sopas, chocolate quente: ↑ no inverno (Nov-Fev × 1.2)
- Restantes: fator 1.0

### Confiança do modelo
```
confidence = min(1.0, num_purchases / 8)
```
- < 4 compras: baixa confiança → sugerir mas com "?" 
- 4-7 compras: média → sugerir normalmente
- 8+ compras: alta → incluir automaticamente na triagem

## Atualização do Modelo

### Após cada compra
1. Adicionar entrada ao `purchase_history` (manter últimos 12)
2. Recalcular `avg_weekly_consumption`
3. Recalcular `avg_purchase_interval_days`
4. Reset `estimated_stock_remaining_days`
5. Atualizar `confidence`

### Feedback do utilizador
- "Ainda temos [X]" → stock durou mais que previsto → aumentar duração estimada em 20%
- "Já acabou o [X]" (antes da previsão) → diminuir duração em 20%
- "Já não compramos [X]" → marcar como inativo (não remover, pode voltar)
- "Passámos a comprar marca Y" → atualizar preferred_brand

## Geração de Lista Proativa

### Stock check diário (cron 10h)
```
Para cada produto ativo no modelo:
  Se estimated_days_left <= 2 E confidence >= 0.5:
    Se produto já está na shopping_list → skip
    Senão → alertar: "⚠️ [Produto] acaba em ~[N] dias"
```

### Triagem semanal (domingo 9h)
```
Para cada produto ativo no modelo:
  Se estimated_days_left <= 9 (cobre até próxima triagem + buffer):
    Calcular quantidade: avg_weekly × 1.15 (15% buffer)
    Se bulk_eligible E próxima_granel > 7 dias:
      Marcar para compra semanal com quantidade normal
    Senão se bulk_eligible E próxima_granel <= 7 dias:
      Marcar para granel com bulk_quantity
    Senão:
      Marcar para compra semanal
```

### Planeamento mensal de granel (dia 25)
```
Para cada produto com bulk_eligible = true:
  Calcular necessidade para 4-5 semanas: avg_weekly × 4.5
  Arredondar para embalagem mais próxima
  Adicionar à lista de granel
```

## Produtos Novos

Quando a família adiciona um produto que não existe no modelo:
1. Criar entrada com valores default:
   - avg_weekly: baseado na quantidade pedida / 1 semana
   - confidence: 0.1
   - bulk_eligible: false
2. Começar a aprender com as compras subsequentes
3. Após 4ª compra: sugerir ao utilizador se quer incluir nas previsões automáticas

## Calibração por Agregado Familiar

Referência de consumo per capita por semana (multiplicar por `household_size` de `family_preferences.json`):

| Categoria | Per capita/semana |
|---|---|
| Leite | ~1L/pessoa |
| Pão | ~1 unidade/pessoa |
| Ovos | ~3-4 unidades/pessoa |
| Fruta | ~700g/pessoa |
| Carne/Peixe | ~600g/pessoa |
| Arroz/Massa | ~300g/pessoa |

O seed data em `data/consumption_model.json` usa valores para um agregado de 4 pessoas como referência.
O agente lê `household_size` de `data/family_preferences.json` — ajustar os valores em `consumption_model.json`
após a primeira compra real para reflectir os hábitos do teu agregado.

Estes são pontos de partida — o modelo ajusta com dados reais ao longo do tempo.
