# 🛒 Grocery Manager PT

> **OpenClaw skill** para gestão autónoma de compras de mercearia em Portugal.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-orange)](https://openclaw.ai)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)

Gere o ciclo completo de compras do teu agregado familiar: mantém inventário, aprende hábitos de consumo, faz triagem semanal, compara preços entre **Continente Online** e **Pingo Doce Online**, e executa compras com aprovação via **WhatsApp** — tudo de forma autónoma a partir do [OpenClaw](https://openclaw.ai).

## Funcionalidades

| Módulo                   | O que faz                                                                       |
| ------------------------ | ------------------------------------------------------------------------------- |
| **Lista de compras**     | Adiciona/remove itens por linguagem natural no WhatsApp                         |
| **Motor de consumo**     | Aprende padrões do agregado e alerta quando produtos estão a acabar             |
| **Triagem semanal**      | Gera proposta de compra todos os domingos, envia ao grupo para aprovação        |
| **Comparação de preços** | Otimiza a lista entre Continente e Pingo Doce (inclui promoções, cupões, saldo) |
| **Compra online**        | Executa o checkout via browser automation — nunca sem aprovação explícita       |
| **Relatórios**           | Resumos semanais e mensais de gastos, poupança e tendências                     |

## Pré-requisitos

- [OpenClaw](https://openclaw.ai) instalado e em execução
- Canal WhatsApp configurado no OpenClaw (`openclaw channels login`)
- Contas activas no [Continente Online](https://www.continente.pt) e/ou [Pingo Doce Online](https://www.pingodoce.pt)
- Python 3.11+

## Instalação

### 1. Copiar a skill para o workspace do OpenClaw

```bash
git clone https://github.com/nmcarv/grocery-manager-pt.git \
  ~/.openclaw/workspace/skills/grocery-manager-pt
```

### 2. Instalar dependências Python

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Configurar credenciais

As credenciais **nunca** são guardadas em ficheiros — são injectadas pelo OpenClaw em tempo de execução:

```bash
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_EMAIL  "email@exemplo.com"
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_PASSWORD "password"
openclaw config set skills.entries.grocery-manager-pt.env.PINGODOCE_EMAIL    "email@exemplo.com"
openclaw config set skills.entries.grocery-manager-pt.env.PINGODOCE_PASSWORD "password"
```

> **Antes de configurar:** recomendamos criar contas dedicadas nos supermercados (email separado, password única) e ligar um cartão MB Way com limite mensal em vez do cartão principal. Ver [Configuração Segura Recomendada](SECURITY.md#configuração-segura-recomendada) para o guia completo, incluindo a progressão gradual de permissões sugerida para as primeiras semanas.

### 4. Configurar o agregado familiar

Copiar o template e editar com os teus dados reais:

```bash
cp data/family_preferences.example.json data/family_preferences.json
```

O ficheiro `family_preferences.json` está no `.gitignore` — os teus dados pessoais (morada, membros da família, budget) ficam apenas na tua máquina e nunca chegam ao repositório.

Campos essenciais a preencher:

```json
{
  "household_size": 4,
  "admin_users": ["O_Teu_Nome"],
  "family_members": ["O_Teu_Nome", "Membro2", "Membro3"],
  "budget": {
    "weekly_limit_eur": 120,
    "monthly_limit_eur": 450,
    "bulk_monthly_budget_eur": 100
  },
  "delivery_preferences": {
    "preferred_days": ["sábado", "domingo"],
    "preferred_time_slots": ["10h-13h"],
    "address": "Rua Exemplo, 123, 1000-001 Lisboa"
  }
}
```

Ver [Referência de Configuração](#referência-de-configuração) para todos os campos disponíveis.

### 5. Configurar cron jobs

```bash
# ID do grupo WhatsApp (obtém com: openclaw channels whatsapp groups)
export GROCERY_WHATSAPP_GROUP="120363000000000000@g.us"

chmod +x scripts/setup_crons.sh
./scripts/setup_crons.sh
```

## Uso

No WhatsApp, qualquer membro do agregado pode escrever:

```
"Acabou o leite"           → adiciona à lista
"Precisamos de 3kg de arroz" → adiciona com quantidade
"Remove as bolachas"        → remove da lista
"Mostra a lista"            → lista categorizada
"Quanto gastámos este mês?" → relatório de gastos
```

Respostas automáticas do bot:

```
✅ Adicionei Leite (2L) à lista. Total: 14 itens.
```

### Crons automáticos

| Schedule           | Ação                                               |
| ------------------ | -------------------------------------------------- |
| Domingo 9h         | Triagem semanal → proposta ao grupo para aprovação |
| Diário 10h         | Stock check → alerta se produto acaba em ≤ 2 dias  |
| Segunda 8h         | Relatório semanal de gastos                        |
| Dia 25 9h          | Planeamento de compra a granel                     |
| Dia 1 9h           | Relatório mensal completo                          |
| Quarta e sábado 6h | Refresh de cache de preços                         |

### Fluxo de aprovação de compra

```
Bot (domingo 9h):
  🛒 Triagem Semanal — 1 Mar 2026
  📦 COMPRA SEMANAL (18 itens): ...
  Respondam com ✅ para aprovar

Família: ✅

Bot:
  💰 Continente (15 itens): €54.20 | Pingo Doce (3 itens): €8.40
  Total: €62.60 — poupança vs. single-store: €5.10
  📸 [screenshot do carrinho]
  ✅ para confirmar | ❌ para cancelar

Admin: ✅

Bot: ✅ Encomenda CON-12345678 confirmada. Entrega: sáb 10h-13h.
```

## Arquitetura

```
grocery-manager-pt/
├── SKILL.md                      # Instruções core lidas pelo agente OpenClaw
├── scripts/
│   ├── price_cache.py            # Persistência de preços (TTL 24h)
│   ├── price_compare.py          # Otimização greedy multi-mercado + cupões
│   ├── consumption_tracker.py    # Modelo de consumo com média ponderada
│   ├── list_optimizer.py         # Geração de lista semanal/granel
│   └── setup_crons.sh            # Configura cron jobs no OpenClaw
├── references/
│   ├── continente_guide.md       # Guia de navegação Continente (browser tool)
│   ├── pingodoce_guide.md        # Guia de navegação Pingo Doce (browser tool)
│   ├── price_comparison_logic.md # Algoritmo de otimização documentado
│   └── consumption_patterns.md   # Modelo de consumo e fórmulas
├── assets/templates/             # Templates de mensagens WhatsApp
├── data/                               # Dados persistentes (editáveis pelo utilizador)
│   ├── family_preferences.example.json # ← Template: copiar para family_preferences.json
│   ├── family_preferences.json         # ← Criado localmente, no .gitignore
│   ├── inventory.json
│   ├── consumption_model.json          # Seed data incluído, aprende com compras reais
│   ├── shopping_history.json
│   └── price_cache.json
└── tests/                        # 73 testes unitários
```

### Browser automation

O agente usa a **browser tool nativa do OpenClaw** (sem seletores CSS hardcoded):

```
browser open "https://www.continente.pt/pesquisa/?q=leite"
browser snapshot   → UI tree com refs numerados
browser act click [ref_add_to_cart]
browser screenshot → enviar para aprovação
```

Esta abordagem é mais resiliente a mudanças no layout dos sites do que scrapers com CSS selectors.

## Referência de Configuração

### `data/family_preferences.json`

> Criado localmente a partir de `family_preferences.example.json`. Nunca commitado — está no `.gitignore`.

| Campo                                       | Tipo         | Descrição                                                  |
| ------------------------------------------- | ------------ | ---------------------------------------------------------- |
| `household_size`                            | int          | Número de pessoas no agregado                              |
| `admin_users`                               | string[]     | Utilizadores com permissão para aprovar compras            |
| `family_members`                            | string[]     | Todos os membros que podem interagir com o bot             |
| `dietary_restrictions`                      | string[]     | Ex: `["sem glúten", "vegetariano"]`                        |
| `brand_preferences`                         | object       | Por produto: `{ "preferred": "...", "acceptable": [...] }` |
| `blocked_items`                             | string[]     | Produtos que nunca devem ser comprados                     |
| `budget.weekly_limit_eur`                   | float        | Limite semanal (compra recusada se ultrapassado)           |
| `budget.monthly_limit_eur`                  | float        | Limite mensal total                                        |
| `budget.bulk_monthly_budget_eur`            | float        | Budget separado para compras a granel                      |
| `delivery_preferences.preferred_days`       | string[]     | Ex: `["sábado", "domingo"]`                                |
| `delivery_preferences.preferred_time_slots` | string[]     | Ex: `["10h-13h"]`                                          |
| `delivery_preferences.address`              | string       | Morada de entrega completa                                 |
| `next_bulk_date`                            | string\|null | ISO date da próxima compra a granel                        |
| `bulk_interval_days`                        | int          | Intervalo entre compras a granel (default: 30)             |

### Variáveis de ambiente

| Variável              | Obrigatória | Descrição                           |
| --------------------- | ----------- | ----------------------------------- |
| `CONTINENTE_EMAIL`    | Sim         | Email da conta Continente Online    |
| `CONTINENTE_PASSWORD` | Sim         | Password da conta Continente Online |
| `PINGODOCE_EMAIL`     | Sim         | Email da conta Pingo Doce Online    |
| `PINGODOCE_PASSWORD`  | Sim         | Password da conta Pingo Doce Online |

## Desenvolvimento

```bash
# Criar venv e instalar dependências (inclui pytest)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Correr testes
.venv/bin/python -m pytest tests/ -v

# Testar um script directamente
.venv/bin/python scripts/consumption_tracker.py check-stock
.venv/bin/python scripts/price_compare.py
.venv/bin/python scripts/list_optimizer.py triage --next-bulk-date 2026-03-01
```

> **Alternativa (ambiente de desenvolvimento local):** activar a venv com `source .venv/bin/activate` e usar `python` / `pytest` directamente no terminal.

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para como contribuir.

## Segurança

Este projeto interage com contas de supermercados e executa compras online.
Ver [SECURITY.md](SECURITY.md) para a política de segurança e como reportar vulnerabilidades.

**Garantias do bot:**

- ❌ Nunca introduz dados bancários (apenas métodos pré-guardados nas contas)
- ❌ Nunca executa checkout sem aprovação explícita do admin no WhatsApp
- ❌ Nunca ultrapassa o budget configurado sem override explícito
- ✅ Todas as ações de browser são logged para auditoria

## Supermercados Suportados

| Supermercado      | Pesquisa | Carrinho | Checkout | Cupões | Saldo    |
| ----------------- | -------- | -------- | -------- | ------ | -------- |
| Continente Online | ✅       | ✅       | ✅       | ✅     | ✅       |
| Pingo Doce Online | ✅       | ✅       | ✅       | ✅     | ✅ Poupa |

Contribuições para outros supermercados são bem-vindas — ver [CONTRIBUTING.md](CONTRIBUTING.md#adicionar-um-novo-supermercado).

## Contribuir

Contribuições são bem-vindas. Ver [CONTRIBUTING.md](CONTRIBUTING.md) para:

- Como fazer setup do ambiente de desenvolvimento
- Como adicionar suporte a novos supermercados
- Como submeter um pull request

## Licença

[MIT](LICENSE) — livre para usar, modificar e distribuir.
