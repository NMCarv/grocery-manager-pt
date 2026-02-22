---
name: grocery-manager-pt
description: >
  Gestão completa de compras de mercearia para famílias em Portugal.
  Mantém inventário da casa, aprende hábitos de consumo, faz triagem semanal,
  compara preços entre Continente Online e Pingo Doce Online, aproveita cupões
  e saldo, executa compras online, e coordena com a família via WhatsApp.
  Usa esta skill quando o utilizador mencionar: compras, supermercado,
  mercearia, lista de compras, Continente, Pingo Doce, "está a faltar",
  "precisamos de", "acabou o", inventário da casa, preços de supermercado,
  cupões, saldo de cartão, compra a granel, compra do mês, ou qualquer
  referência a alimentos, produtos de limpeza, ou artigos domésticos.
  Também se ativa automaticamente via cron para triagem semanal e stock checks.
emoji: 🛒
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - curl
        - jq
      env:
        - CONTINENTE_EMAIL
        - CONTINENTE_PASSWORD
        - PINGODOCE_EMAIL
        - PINGODOCE_PASSWORD
    install:
      - id: pip-deps
        kind: exec
        command: "pip3 install requests beautifulsoup4 playwright aiohttp"
        label: "Install Python dependencies"
      - id: playwright-browsers
        kind: exec
        command: "python3 -m playwright install chromium"
        label: "Install Playwright Chromium"
---

# Grocery Manager PT 🛒

Skill de gestão de compras de mercearia para uma família de 7 pessoas em Portugal.
Opera em ciclo contínuo: inventário → previsão → triagem → comparação → compra → tracking.

## Quando Usar

- Qualquer pedido sobre lista de compras (adicionar, remover, consultar)
- Triagem semanal (cron: domingo 9h) ou quando pedido manualmente
- Comparação de preços entre supermercados
- Execução de compras online (Continente, Pingo Doce)
- Relatórios de gastos e consumo
- Planeamento de compra a granel mensal

## Dados Persistentes

Todos os ficheiros de dados vivem em `data/` dentro desta skill:

| Ficheiro | Propósito |
|---|---|
| `data/inventory.json` | Lista de compras ativa + estado do inventário |
| `data/shopping_history.json` | Histórico de todas as compras realizadas |
| `data/consumption_model.json` | Modelo de consumo aprendido (frequências, quantidades) |
| `data/family_preferences.json` | Preferências da família (marcas, budget, restrições) |
| `data/price_cache.json` | Cache de preços recentes por supermercado |

**Antes de qualquer ação, lê os ficheiros de dados relevantes.** Se não existirem, cria-os a partir dos templates em `data/`.

## Módulo 1 — Gestão da Lista de Compras

### Adicionar itens
Quando alguém diz "acabou o X", "precisamos de Y", "adiciona Z":
1. Lê `data/inventory.json`
2. Parseia o item: nome, quantidade (default: 1un), categoria (infere automaticamente)
3. Verifica duplicados (match fuzzy — "leite" e "leite meio gordo" merecem confirmação)
4. Adiciona ao array `shopping_list` com metadata (quem adicionou, quando, prioridade)
5. Grava ficheiro
6. Confirma: "✅ Adicionei [item] à lista. Total: N itens."

### Remover itens
Quando alguém diz "remove X", "já não preciso de Y", "já comprámos Z":
1. Lê `data/inventory.json`
2. Encontra match no `shopping_list` (fuzzy)
3. Remove e grava
4. Confirma: "✅ Removi [item]. Total: N itens."

### Consultar lista
Quando alguém diz "mostra a lista", "o que falta comprar":
1. Lê `data/inventory.json`
2. Agrupa `shopping_list` por categoria
3. Formata com emojis por categoria:
   - 🥛 Lacticínios | 🥩 Proteína | 🥬 Frescos | 🍞 Padaria
   - 🧹 Limpeza | 🧴 Higiene | 🥤 Bebidas | 🍪 Snacks | 📦 Outros
4. Envia lista categorizada

### Categorias e emojis

```
lacticínios → 🥛   proteína → 🥩    frescos → 🥬     padaria → 🍞
limpeza → 🧹       higiene → 🧴     bebidas → 🥤     snacks → 🍪
congelados → 🧊    conservas → 🥫   temperos → 🌿    outros → 📦
```

## Módulo 2 — Motor de Hábitos de Consumo

Lê `references/consumption_patterns.md` para a lógica completa.

**Resumo:** O modelo em `data/consumption_model.json` guarda, por produto:
- Consumo médio semanal (quantidade + unidade)
- Intervalo médio entre compras
- Marca preferida e alternativas aceitáveis
- Data da última compra + stock estimado restante
- Flag de elegibilidade para compra a granel
- Fator sazonal

**Atualização:** Após cada compra, atualiza o modelo com os dados reais. Depois de 4+ compras do mesmo produto, as previsões tornam-se fiáveis.

**Alertas proativos:** No stock check diário (cron 10h), se um produto tem ≤2 dias de stock estimado:
- Envia alerta: "⚠️ [Produto] deve acabar em ~2 dias. Adicionar à lista?"
- Se o utilizador confirma → adiciona à shopping_list
- Se o utilizador diz "ainda temos" → ajusta o modelo (aumenta duração estimada em 20%)

## Módulo 3 — Triagem Semanal

**Trigger:** Cron domingo 9h WET, ou manualmente ("faz a triagem", "prepara a lista da semana").

### Fluxo

1. **Consolidar:** Merge itens manuais (shopping_list) + previsões do modelo de consumo
2. **Separar:** Compra semanal vs. itens para granel (se próxima granel > 7 dias)
3. **Quantificar:** Calcular quantidades baseadas no consumo médio × 7 dias (+15% buffer)
4. **Verificar:** Cruzar com `family_preferences.json` (blocklist, budget)
5. **Formatar:** Usar template `assets/templates/weekly_triage.md`
6. **Enviar:** Proposta ao grupo WhatsApp
7. **Aguardar:** Feedback durante 4h — processar respostas (adicionar/remover/aprovar)
8. **Fechar:** Após aprovação (✅ do admin) ou timeout com maioria → avançar para comparação

### Formato da proposta
```
🛒 Triagem Semanal — [DATA]

📦 COMPRA SEMANAL ([N] itens):
[items agrupados por categoria com emoji]

📦 PARA GRANEL (próxima: [DATA]):
[items com quantidades bulk]

⚠️ ALERTAS:
[produtos urgentes ou observações]

💰 Budget semanal: €[LIMITE]

Respondam com ✅ para aprovar, ou adicionem/removam itens.
```

## Módulo 4 — Comparação de Preços

Lê `references/price_comparison_logic.md` para o algoritmo completo.

**Resumo:** Executa `scripts/price_compare.py` que:
1. Para cada item da lista, pesquisa preço em Continente + Pingo Doce (usa cache se <24h)
2. Normaliza para preço unitário (€/kg, €/L, €/un)
3. Considera promoções ativas e cupões disponíveis na conta
4. Corre otimização: minimiza custo total incluindo entrega
5. Se diferença entre 1 vs 2 mercados < €5 → recomenda 1 mercado (simplicidade)
6. Output: plano com split por mercado, poupança estimada, cupões a aplicar

**Formato do relatório:** Usa template `assets/templates/price_comparison.md`

## Módulo 5 — Execução de Compras Online

Lê `references/continente_guide.md` ou `references/pingodoce_guide.md` conforme o mercado.

### Regras CRÍTICAS
- ❌ **NUNCA** introduzir dados de cartão de crédito/débito
- ❌ **NUNCA** finalizar checkout sem ✅ explícito do admin
- ❌ **NUNCA** ultrapassar budget sem override explícito
- ✅ Usar apenas métodos de pagamento pré-guardados na conta
- ✅ Screenshot do carrinho antes de confirmar → enviar para aprovação
- ✅ Log de todas as ações de browser

### Fluxo por supermercado
1. **Login** → credenciais de env vars → verificar sessão ativa
2. **Cupões** → navegar à área de cupões → ativar relevantes → registar saldo
3. **Carrinho** → para cada item: pesquisar → selecionar melhor match → adicionar
4. **Indisponíveis** → se produto não encontrado: notificar, sugerir alternativa, aguardar
5. **Revisão** → comparar total real vs estimativa → se diff >10%: pausa + notifica
6. **Aprovação** → screenshot → enviar ao admin → aguardar ✅
7. **Checkout** → slot de entrega → cupões → confirmar → gravar nº encomenda
8. **Pós-compra** → atualizar inventory, shopping_history, consumption_model

### Browser config
Usa profile `grocery` (isolado). Delays humanizados: 1-3s entre cliques, 0.5-1s entre teclas.
Se CAPTCHA → pausa e notifica. Se bloqueio → cooldown 24h.

## Módulo 6 — Coordenação Familiar (WhatsApp)

### Comandos suportados
| Input | Ação |
|---|---|
| "Acabou o [X]" / "Precisamos de [X]" | Adiciona à lista |
| "Remove [X]" / "Já não preciso de [X]" | Remove da lista |
| "Mostra a lista" / "O que falta?" | Envia lista categorizada |
| "Quanto gastámos?" | Resumo de gastos do mês |
| "Quando chega a encomenda?" | Info de tracking |
| ✅ (resposta a proposta) | Voto de aprovação |
| ❌ (resposta a proposta) | Voto de rejeição |

### Regras de comunicação
- Respostas curtas (WhatsApp ≠ email)
- Emojis para categorias
- Máximo 3 mensagens proativas/dia
- Quiet hours: 22h–8h
- Qualquer membro adiciona itens; apenas admin (Nuno) aprova compras

## Módulo 7 — Relatórios

Cron segunda 8h → relatório semanal. Cron dia 1 9h → relatório mensal.
Templates em `assets/templates/`. Dados de `data/shopping_history.json`.

**Semanal:** Total gasto, breakdown por mercado, poupança, cupões usados.
**Mensal:** Média semanal, % por categoria, tendências de preço, poupança acumulada.

## Scripts

| Script | Propósito | Quando usar |
|---|---|---|
| `scripts/scrape_continente.py` | Pesquisar preços/produtos no Continente | Comparação de preços |
| `scripts/scrape_pingodoce.py` | Pesquisar preços/produtos no Pingo Doce | Comparação de preços |
| `scripts/price_compare.py` | Otimização multi-mercado | Após triagem aprovada |
| `scripts/consumption_tracker.py` | Atualizar modelo de consumo | Após cada compra |
| `scripts/list_optimizer.py` | Gerar lista semanal/mensal otimizada | Triagem semanal/mensal |

## Referências

Lê estes ficheiros **conforme necessário** (não carregar todos de uma vez):

| Ficheiro | Quando ler |
|---|---|
| `references/continente_guide.md` | Quando interagir com Continente Online |
| `references/pingodoce_guide.md` | Quando interagir com Pingo Doce Online |
| `references/price_comparison_logic.md` | Quando correr comparação de preços |
| `references/consumption_patterns.md` | Quando atualizar/consultar modelo de consumo |
