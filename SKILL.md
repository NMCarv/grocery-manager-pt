---
name: grocery-manager-pt
description: >
  Gestão completa de compras de mercearia para famílias em Portugal.
  Mantém inventário da casa, aprende hábitos de consumo, faz triagem semanal,
  compara preços entre Continente Online e Pingo Doce Online, aproveita cupões
  e saldo, executa compras online, e coordena com a família via WhatsApp.
  Também gera lembretes de compras presenciais para lojas sem entrega online
  (Lidl, Makro, Auchan, etc.) com base em preferências configuradas.
  Usa esta skill quando o utilizador mencionar: compras, supermercado,
  mercearia, lista de compras, Continente, Pingo Doce, Lidl, Makro, Auchan,
  "está a faltar", "precisamos de", "acabou o", inventário da casa, preços de
  supermercado, cupões, saldo de cartão, compra a granel, compra do mês, ou
  qualquer referência a alimentos, produtos de limpeza, ou artigos domésticos.
  Também se ativa automaticamente via cron para triagem semanal e stock checks.
emoji: 🛒
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - jq
      env:
        - CONTINENTE_EMAIL
        - CONTINENTE_PASSWORD
        - PINGODOCE_EMAIL
        - PINGODOCE_PASSWORD
    install:
      - id: pip-deps
        kind: exec
        command: "pip3 install requests aiohttp"
        label: "Instalar dependências Python"
---

# Grocery Manager PT 🛒

Skill de gestão de compras de mercearia para famílias em Portugal.
Opera em ciclo contínuo: inventário → previsão → triagem → comparação → compra → tracking.

O tamanho do agregado familiar, membros, orçamento e preferências de entrega são lidos de
`{baseDir}/data/family_preferences.json`. Configurar este ficheiro antes de usar a skill.

**Diretório da skill:** `{baseDir}`

## Quando Usar

- Qualquer pedido sobre lista de compras (adicionar, remover, consultar)
- Triagem semanal (cron: domingo 9h) ou quando pedido manualmente
- Comparação de preços entre supermercados
- Execução de compras online (Continente, Pingo Doce)
- Relatórios de gastos e consumo
- Planeamento de compra a granel mensal

## Dados Persistentes

Todos os ficheiros de dados vivem em `{baseDir}/data/`:

| Ficheiro | Propósito |
|---|---|
| `{baseDir}/data/inventory.json` | Lista de compras ativa + estado do inventário |
| `{baseDir}/data/shopping_history.json` | Histórico de todas as compras realizadas |
| `{baseDir}/data/consumption_model.json` | Modelo de consumo aprendido (frequências, quantidades) |
| `{baseDir}/data/family_preferences.json` | Preferências da família (marcas, budget, restrições) |
| `{baseDir}/data/price_cache.json` | Cache de preços recentes por supermercado |

**Antes de qualquer ação, lê os ficheiros de dados relevantes.**

## Módulo 1 — Gestão da Lista de Compras

### Adicionar itens
Quando alguém diz "acabou o X", "precisamos de Y", "adiciona Z":
1. Lê `{baseDir}/data/inventory.json`
2. Parseia o item: nome, quantidade (default: 1un), categoria (infere automaticamente)
3. Verifica duplicados (match fuzzy — "leite" e "leite meio gordo" merecem confirmação)
4. Adiciona ao array `shopping_list` com metadata (quem adicionou, quando, prioridade)
5. Grava ficheiro
6. Confirma: "✅ Adicionei [item] à lista. Total: N itens."

### Remover itens
Quando alguém diz "remove X", "já não preciso de Y", "já comprámos Z":
1. Lê `{baseDir}/data/inventory.json`
2. Encontra match no `shopping_list` (fuzzy)
3. Remove e grava
4. Confirma: "✅ Removi [item]. Total: N itens."

### Consultar lista
Quando alguém diz "mostra a lista", "o que falta comprar":
1. Lê `{baseDir}/data/inventory.json`
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

Lê `{baseDir}/references/consumption_patterns.md` para a lógica completa.

**Resumo:** O modelo em `{baseDir}/data/consumption_model.json` guarda, por produto:
- Consumo médio semanal (quantidade + unidade)
- Intervalo médio entre compras
- Marca preferida e alternativas aceitáveis
- Data da última compra + stock estimado restante
- Flag de elegibilidade para compra a granel
- `preferred_store`: `null` = compra online (Continente/Pingo Doce); string = loja presencial (ex: `"lidl"`)
- Fator sazonal

**Atualização:** Após cada compra, executa:
```
python3 {baseDir}/scripts/consumption_tracker.py update --purchase <ficheiro_compra.json>
```

**Alertas proativos:** No stock check diário (cron 10h):
```
python3 {baseDir}/scripts/consumption_tracker.py check-stock
```
Se um produto tem ≤2 dias de stock estimado:
- Envia alerta: "⚠️ [Produto] deve acabar em ~2 dias. Adicionar à lista?"
- Se o utilizador confirma → adiciona à shopping_list
- Se o utilizador diz "ainda temos" → executa:
  `python3 {baseDir}/scripts/consumption_tracker.py feedback --product "[nome]" --type still_have`

## Módulo 3 — Triagem Semanal

**Trigger:** Cron domingo 9h WET, ou manualmente ("faz a triagem", "prepara a lista da semana").

### Fluxo

1. **Gerar lista:** `python3 {baseDir}/scripts/list_optimizer.py triage --next-bulk-date [DATA]`
2. **Verificar:** Cruzar com `{baseDir}/data/family_preferences.json` (blocklist, budget)
3. **Formatar:** Usar template `{baseDir}/assets/templates/weekly_triage.md`
4. **Enviar:** Proposta ao grupo WhatsApp
5. **Aguardar:** Feedback durante 4h — processar respostas (adicionar/remover/aprovar)
6. **Fechar:** Após aprovação (✅ do admin) ou timeout com maioria → avançar para comparação

### Lojas presenciais (physical_items)

O resultado do `triage` inclui o campo `physical_items` — produtos com `preferred_store` definido
em `consumption_model.json`. Estes itens **nunca entram na comparação de preços online** nem no
carrinho do Continente/Pingo Doce. São incluídos na mensagem de triagem como lembrete de visita presencial.

Exemplos de uso:
- `"preferred_store": "lidl"` — café que o utilizador prefere comprar no Lidl
- `"preferred_store": "makro"` — granel (arroz, azeite) comprado no Makro/Recheio
- `"preferred_store": "auchan"` — produto específico só disponível no Auchan

As lojas físicas são configuradas em `{baseDir}/data/family_preferences.json` → `physical_stores`
(nome de exibição, frequência de visita, notas). Para listar apenas compras presenciais:
```
python3 {baseDir}/scripts/list_optimizer.py physical
```

### Formato da proposta
```
🛒 Triagem Semanal — [DATA]

📦 COMPRA SEMANAL ([N] itens):
[items agrupados por categoria com emoji]

📦 PARA GRANEL (próxima: [DATA]):
[items com quantidades bulk]

🏪 COMPRAS PRESENCIAIS:
[LOJA 1] ([N] itens — visita [frequência]):
  • [produto] — [quantidade] [unidade] ([marca])
[LOJA 2] ...

⚠️ ALERTAS:
[produtos urgentes ou observações]

💰 Budget semanal: €[LIMITE]

Respondam com ✅ para aprovar, ou adicionem/removam itens.
```

Se não houver compras presenciais pendentes, omitir a secção 🏪.

## Módulo 4 — Comparação de Preços

Lê `{baseDir}/references/price_comparison_logic.md` para o algoritmo completo.

**Resumo do fluxo:**
1. Para cada item da lista, verificar cache: `{baseDir}/data/price_cache.json`
2. Se cache expirado (<24h) → recolher preços via browser tool (ver abaixo)
3. Executar otimização: `python3 {baseDir}/scripts/price_compare.py --output /tmp/comparison.json`
4. Formatar resultado usando template `{baseDir}/assets/templates/price_comparison.md`
5. Enviar ao grupo WhatsApp para aprovação

### Recolha de preços via browser tool

Para cada produto em falta no cache:
1. `browser open "https://www.continente.pt/pesquisa/?q=[produto]"`
2. `browser snapshot` → identificar card do produto mais relevante
3. Extrair nome, preço, preço por unidade, promoção ativa
4. Gravar no cache: `python3 {baseDir}/scripts/price_cache.py update --market continente --product "[nome]" --data '[json]'`
5. Repetir para Pingo Doce: `https://www.pingodoce.pt/pesquisa/?q=[produto]`

## Módulo 5 — Execução de Compras Online

Lê `{baseDir}/references/continente_guide.md` ou `{baseDir}/references/pingodoce_guide.md` conforme o mercado.

### Regras CRÍTICAS (sem exceções)
- ❌ **NUNCA** introduzir dados de cartão de crédito/débito
- ❌ **NUNCA** finalizar checkout sem ✅ explícito do admin no WhatsApp
- ❌ **NUNCA** ultrapassar budget sem override explícito
- ✅ Usar apenas métodos de pagamento pré-guardados na conta
- ✅ Tirar screenshot do carrinho antes de confirmar → enviar para aprovação
- ✅ Registar número de encomenda em `{baseDir}/data/shopping_history.json`

### Fluxo por supermercado (usando browser tool)

**1. Login**
- Navegar à página de login do supermercado (ver guide de referência)
- `browser snapshot` → identificar campos de email e password
- `browser act type [ref_email] "$CONTINENTE_EMAIL"` (ou PINGODOCE_EMAIL)
- `browser act type [ref_password] "$CONTINENTE_PASSWORD"` (ou PINGODOCE_PASSWORD)
- `browser act click [ref_submit]`
- `browser snapshot` → verificar se login foi bem sucedido (nome do utilizador visível)
- Se 2FA solicitado: PAUSA, notificar utilizador, aguardar resolução manual

**2. Verificar cupões**
- Navegar à área de cupões (ver URL no guide de referência)
- `browser snapshot` → identificar lista de cupões disponíveis
- Ativar cupões relevantes para a compra atual
- Registar valor total de cupões

**3. Construir carrinho**
Para cada item do plano deste mercado:
- Navegar à pesquisa com o nome do produto
- `browser snapshot` → identificar o produto mais relevante (marca preferida > aceitável > marca própria)
- Se indisponível: notificar família, sugerir alternativa, aguardar feedback
- `browser act click [ref_add_to_cart]`
- Se quantidade > 1: ajustar no carrinho
- Delay de 2-3 segundos entre adições
- Se CAPTCHA aparecer: PAUSA, notificar utilizador, aguardar resolução

**4. Revisão e aprovação**
- Navegar ao carrinho
- `browser snapshot` → verificar total
- Se total difere >10% da estimativa: PAUSA, notificar utilizador
- `browser screenshot` → enviar imagem ao admin no WhatsApp
- Mensagem: "🛒 Carrinho [Mercado] pronto. Total: €[X]. Aprovação: ✅ confirmar | ❌ cancelar"
- **AGUARDAR ✅ explícito antes de avançar**

**5. Checkout**
Após ✅ do admin:
- Prosseguir para checkout
- Confirmar morada de entrega
- Selecionar slot (preferir sábado/domingo 10h-13h, grátis se disponível)
- Confirmar método de pagamento pré-guardado (nunca introduzir dados novos)
- `browser screenshot` → última verificação
- Confirmar encomenda
- Extrair número de encomenda da página de confirmação

**6. Pós-compra**
- Atualizar `{baseDir}/data/shopping_history.json` com dados da compra
- Executar: `python3 {baseDir}/scripts/consumption_tracker.py update --purchase <dados.json>`
- Notificar família: "✅ Encomenda [Nº] confirmada. Entrega: [slot]. Total: €[X]"

## Módulo 6 — Coordenação Familiar (WhatsApp)

### Comandos suportados
| Input | Ação |
|---|---|
| "Acabou o [X]" / "Precisamos de [X]" | Adiciona à lista |
| "Remove [X]" / "Já não preciso de [X]" | Remove da lista |
| "Mostra a lista" / "O que falta?" | Envia lista categorizada |
| "Quanto gastámos?" / "Quanto gastámos este mês?" | Resumo de gastos do mês |
| "Quando chega a encomenda?" | Info de tracking |
| "Ainda temos [X]" | Ajusta modelo de consumo (still_have) |
| "Já acabou o [X]" | Ajusta modelo de consumo (already_finished) |
| "Já não compramos [X]" | Desativa produto no modelo |
| ✅ (resposta a proposta) | Voto de aprovação |
| ❌ (resposta a proposta) | Voto de rejeição |

### Regras de comunicação
- Respostas curtas (WhatsApp ≠ email)
- Emojis para categorias e confirmações
- Máximo 3 mensagens proativas/dia (não contar respostas a pedidos)
- Quiet hours: 22h–8h (exceto alertas de stock urgente explicitamente pedidos)
- Qualquer membro da família pode adicionar/remover itens
- Apenas utilizadores em `admin_users` (ver `{baseDir}/data/family_preferences.json`) podem aprovar compras e ultrapassar budgets

## Módulo 7 — Relatórios

**Semanal (cron segunda 8h):**
- Ler `{baseDir}/data/shopping_history.json` (última semana)
- Usar template `{baseDir}/assets/templates/weekly_report.md`
- Enviar ao grupo WhatsApp

**Mensal (cron dia 1 9h):**
- Ler histórico do mês anterior
- Calcular: total, média semanal, % por categoria, poupança acumulada, tendências
- Enviar relatório completo ao grupo

## Scripts

| Script | Propósito | Como usar |
|---|---|---|
| `{baseDir}/scripts/price_cache.py` | Gerir cache de preços | `python3 ... search --product "leite"` |
| `{baseDir}/scripts/price_compare.py` | Otimização multi-mercado | `python3 ... --output /tmp/comparison.json` |
| `{baseDir}/scripts/consumption_tracker.py` | Atualizar/consultar modelo de consumo | `python3 ... check-stock` |
| `{baseDir}/scripts/list_optimizer.py` | Gerar lista semanal/mensal otimizada | `python3 ... triage --next-bulk-date YYYY-MM-DD` |

## Referências

Carregar **apenas quando necessário** (não carregar todos de uma vez):

| Ficheiro | Quando ler |
|---|---|
| `{baseDir}/references/continente_guide.md` | Quando interagir com Continente Online |
| `{baseDir}/references/pingodoce_guide.md` | Quando interagir com Pingo Doce Online |
| `{baseDir}/references/price_comparison_logic.md` | Quando correr comparação de preços |
| `{baseDir}/references/consumption_patterns.md` | Quando atualizar/consultar modelo de consumo |

## Cron Jobs

Configurar com `{baseDir}/scripts/setup_crons.sh`. Jobs ativos:

| Job | Schedule | Ação |
|---|---|---|
| `daily-stock-check` | Diário 10h | Verificar stock e alertar se necessário |
| `weekly-triage` | Domingo 9h | Triagem completa + proposta ao WhatsApp |
| `monthly-bulk-planning` | Dia 25 9h | Planear compra a granel do mês seguinte |
| `weekly-report` | Segunda 8h | Relatório semanal de gastos |
| `monthly-report` | Dia 1 9h | Relatório mensal completo |
| `price-cache-refresh` | Quarta e sábado 6h | Atualizar cache dos 50 produtos mais comprados |
