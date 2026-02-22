# AGENTS.md — grocery-manager-pt

Instruções para agentes de IA que trabalham neste repositório.

## O que é este projeto

**grocery-manager-pt** é uma skill para o [OpenClaw](https://openclaw.ai) que gere
de forma autónoma o ciclo completo de compras de mercearia em Portugal:
inventário → previsão de consumo → triagem semanal → comparação de preços → compra online → tracking.

O agente OpenClaw lê `SKILL.md` (instruções operacionais) e usa os scripts Python como
utilitários de dados. A navegação nos sites dos supermercados é feita pela **browser tool
nativa do OpenClaw** — não por Playwright ou seletores CSS hardcoded.

## Arquitectura

```
SKILL.md                  ← Lido pelo agente OpenClaw em runtime (instruções operacionais)
scripts/                  ← Utilitários Python (dados, cálculos, cache)
references/               ← Guias de navegação por supermercado (browser tool)
assets/templates/         ← Templates de mensagens WhatsApp
data/                     ← Dados persistentes (JSON, editáveis pelo utilizador)
tests/                    ← 113 testes unitários (pytest)
```

### Fluxo de dados

```
WhatsApp (família)
    ↓
OpenClaw Agent (lê SKILL.md + references/)
    ↓
scripts/list_optimizer.py     ← gera lista semanal/granel/presencial
scripts/consumption_tracker.py ← actualiza modelo de consumo
scripts/price_cache.py        ← persiste preços extraídos via browser tool
scripts/price_compare.py      ← optimiza split multi-mercado
    ↓
data/*.json                   ← estado persistente
    ↓
Browser Tool (OpenClaw) → Continente/Pingo Doce → compra executada
```

## Ficheiros-chave

| Ficheiro                         | Propósito                                                                         | Quando modificar                                     |
| -------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `SKILL.md`                       | Instruções do agente OpenClaw. Usa `{baseDir}` para caminhos.                     | Ao mudar o comportamento do agente                   |
| `scripts/config.py`              | Fonte única de verdade: `OnlineMarket` enum, `DELIVERY_CONFIG`, `ONLINE_MARKET_IDS` | Ao adicionar/remover supermercado online             |
| `scripts/price_cache.py`         | Cache de preços (TTL 24h), fuzzy search, parsing de preços PT (`1,29 €` → `1.29`) | Ao mudar estrutura do cache                          |
| `scripts/price_compare.py`       | Otimização greedy multi-mercado com cupões, saldo, threshold de entrega           | Ao mudar algoritmo de preços                         |
| `scripts/consumption_tracker.py` | Modelo de consumo: média ponderada (mais recente = maior peso), alertas, feedback | Ao mudar modelo de previsão                          |
| `scripts/list_optimizer.py`      | Gera lista semanal/granel/triage/presencial a partir do modelo e inventário       | Ao mudar geração de lista                            |
| `scripts/setup_crons.sh`         | Configura 6 cron jobs no OpenClaw via CLI                                         | Ao adicionar/remover crons                           |
| `references/continente_guide.md` | Guia de navegação Continente (linguagem natural, sem CSS selectors)               | Quando o site mudar                                  |
| `references/pingodoce_guide.md`  | Guia de navegação Pingo Doce (idem)                                               | Quando o site mudar                                  |
| `data/family_preferences.json`   | Config do utilizador: household_size, admin_users, budget, morada                 | Template de exemplo — não colocar dados reais em PRs |
| `data/consumption_model.json`    | Seed data + dados aprendidos em runtime                                           | Seed data incluído; runtime data gerado pelo agente  |

## Comandos essenciais

```bash
# Criar venv e instalar dependências (primeira vez)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Correr todos os testes (obrigatório antes de qualquer PR)
.venv/bin/python -m pytest tests/ -v

# Correr um script directamente
.venv/bin/python scripts/consumption_tracker.py check-stock
.venv/bin/python scripts/price_compare.py
.venv/bin/python scripts/list_optimizer.py triage --next-bulk-date 2026-03-01
.venv/bin/python scripts/list_optimizer.py physical
.venv/bin/python scripts/price_cache.py stats
.venv/bin/python scripts/price_cache.py parse-price "2,49 €"
```

Não existe Makefile nem passo de build — os scripts são executados directamente.
O venv é criado em `.venv/` na raiz do projecto e excluído do git.

## Testes

Os testes estão em `tests/` e usam pytest com fixtures em `tests/fixtures/`.

```bash
.venv/bin/python -m pytest tests/ -v           # todos os testes
.venv/bin/python -m pytest tests/test_price_compare.py -v   # um ficheiro
.venv/bin/python -m pytest tests/ -k "coupon"  # por keyword
```

**113 testes — todos devem passar antes de qualquer commit ou PR.**

O `conftest.py` na raiz injeta `scripts/` no `sys.path` do pytest.
O `pyproject.toml` configura `testpaths = ["tests"]` e `pythonpath = ["scripts"]`.

Ao adicionar código novo, adicionar testes correspondentes em `tests/test_<módulo>.py`.
Para novos scripts Python, criar `tests/test_<nome_script>.py`.

## Convenções de código

- **Python 3.11+** — usar type hints onde útil (especialmente em assinaturas de funções)
- **Indentação:** 4 espaços
- **Sem formatter obrigatório** — seguir o estilo existente
- **Docstrings:** em português (o projecto é PT-focused)
- **Retorno de erros:** dicionário `{"error": "mensagem"}` — não lançar excepções nos comandos CLI
- **JSON persistente:** `json.dump(..., ensure_ascii=False)` — preservar caracteres PT (ã, ç, é, etc.)
- **Caminhos:** usar `pathlib.Path`, não `os.path`
- **Datas:** usar `datetime.now(timezone.utc)` para timestamps UTC; `datetime.now()` (naive) para comparações com datas simples (YYYY-MM-DD)

### Mensagens de commit

Seguir [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: adicionar suporte a Auchan Online
fix: corrigir cálculo de média ponderada
docs: actualizar guide do Pingo Doce
test: adicionar testes para apply_coupons
refactor: simplificar fuzzy search no price_cache
```

## Modelo de dados

### `data/family_preferences.json`

Config do utilizador. **Não commitar com dados reais** — é um template de exemplo.
Campos importantes: `household_size`, `admin_users`, `budget.*`, `delivery_preferences.address`.

Campo `physical_stores`: dicionário de lojas físicas onde o utilizador compra presencialmente
(Lidl, Makro, Auchan, etc.). Cada entrada tem `name`, `visit_frequency`, `notes`. As chaves que
começam por `_` (ex: `_exemplo_auchan`) são ignoradas pelo script e servem apenas como exemplos.

### `data/consumption_model.json`

Chave = product_id (snake_case do nome). Campos críticos:

- `avg_weekly_consumption.value` — consumo médio semanal
- `estimated_stock_remaining_days` — calculado em runtime pelo tracker
- `confidence` — entre 0.0 e 1.0. Abaixo de 0.5: produto não aparece em previsões automáticas
- `bulk_eligible` — se `true`, aparece nas listas de granel
- `preferred_store` — `null` = compra online (Continente/Pingo Doce); string = loja presencial
  (ex: `"lidl"`, `"makro"`). Itens com preferred_store **não entram** na comparação de preços
  online nem no carrinho — aparecem apenas como lembretes de visita em `physical_items`.

### `data/price_cache.json`

Estrutura: `{ "continente": { "nome_produto": { price, cached_at, ... } } }`.
TTL: 24h. Verificar com `scripts/price_cache.py expired`.

### `data/inventory.json`

`shopping_list`: array de itens adicionados manualmente pela família.
`items`: inventário actual (preenchido em runtime).

## Regras importantes para agentes de IA

### NÃO fazer

- **Não hardcodar seletores CSS** nos scripts Python ou nos guides de referência — o agente usa browser snapshots
- **Não usar Playwright** — foi deliberadamente removido; a browser tool do OpenClaw substitui-o
- **Não commitar dados pessoais** — `data/family_preferences.json` é um template; `data/shopping_history.json` e `data/consumption_model.json` não devem conter dados reais em PRs
- **Não introduzir dados bancários** em nenhum fluxo de automação — é uma garantia de segurança central do projecto
- **Não contornar a aprovação do admin** no fluxo de checkout — toda a compra requer `✅` explícito
- **Não remover o `ensure_ascii=False`** nos `json.dump()` — quebra caracteres portugueses
- **Não tentar comprar online** itens com `preferred_store` definido — esses itens são exclusivamente presenciais
- **Não quebrar os 113 testes existentes** sem justificação documentada

### Atenção especial

- **`{baseDir}`** em `SKILL.md` é uma variável do OpenClaw injectada em runtime — não substituir por caminhos hardcoded
- **`weighted_average()`** em `consumption_tracker.py` dá mais peso ao ÚLTIMO elemento da lista (mais recente). Esta lógica foi corrigida de um bug — não reverter
- **`datetime.fromisoformat(date_string)`** com datas simples (`YYYY-MM-DD`) retorna datetime naive — comparar com `datetime.now()` (não `datetime.now(timezone.utc)`) para evitar TypeError
- **`config.py`** é a única fonte de verdade para integrações de mercado — `price_compare.py`, `price_cache.py` e `list_optimizer.py` importam `MARKETS`, `ONLINE_MARKET_IDS` e `DELIVERY_CONFIG` daqui. Os testes que fazem `pc.MARKETS` ou `pc.DELIVERY_CONFIG` continuam a funcionar porque são re-exportados do `price_compare`

## Adicionar um novo supermercado

1. Criar `references/NOME_guide.md` (seguir estrutura do `continente_guide.md`)
2. Em `scripts/config.py` — **única fonte de verdade para integrações**:
   - Adicionar membro ao enum `OnlineMarket`
   - Adicionar entrada ao `DELIVERY_CONFIG`
3. Adicionar env vars ao frontmatter de `SKILL.md` (`requires.env`)
4. Actualizar tabela de supermercados no `README.md`
5. Adicionar testes em `tests/test_price_compare.py` para o novo mercado
6. Actualizar `CHANGELOG.md`

`price_cache.py`, `price_compare.py` e `list_optimizer.py` derivam `MARKETS` automaticamente
do enum — não precisam de ser alterados quando se adiciona um novo mercado.

Ver `CONTRIBUTING.md` para guia detalhado.

## Adicionar uma loja presencial

Para registar que o utilizador prefere comprar certos produtos presencialmente (Lidl, Makro, Auchan, etc.):

1. Adicionar a loja a `data/family_preferences.json` → `physical_stores`:
   ```json
   "lidl": { "name": "Lidl", "visit_frequency": "semanal", "notes": "Café e produtos sazonais" }
   ```
2. Nos produtos relevantes em `data/consumption_model.json`, definir `"preferred_store": "lidl"`
3. Esses produtos **não entram** em `generate_weekly_list()`, `generate_bulk_list()`, nem em `price_compare.py`
4. Aparecem em `generate_physical_list()` e no campo `physical_items` da triagem

Não é necessário criar guides de navegação nem credenciais — não há compra online.

## Segurança

Este projecto lida com credenciais de supermercados e executa compras online.
Ver `SECURITY.md` para a política completa.

**Resumo para agentes:** Credenciais chegam via env vars (`CONTINENTE_EMAIL`, etc.) — nunca aparecem em ficheiros. O bot nunca introduz dados bancários. Todo o checkout requer aprovação humana.
