# 🛒 Grocery Manager PT

Skill OpenClaw para gestão completa de compras de mercearia em Portugal.

## Setup

### 1. Credenciais

```bash
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_EMAIL "email@example.com"
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_PASSWORD "password"
openclaw config set skills.entries.grocery-manager-pt.env.PINGODOCE_EMAIL "email@example.com"
openclaw config set skills.entries.grocery-manager-pt.env.PINGODOCE_PASSWORD "password"
```

### 2. Dependências

```bash
pip3 install requests beautifulsoup4 playwright aiohttp
python3 -m playwright install chromium
```

### 3. Configuração

Editar `data/family_preferences.json`:
- Nomes dos membros da família
- Morada de entrega
- Budget semanal/mensal
- Dias e horários preferidos de entrega

### 4. Seletores dos Sites

Preencher os seletores `TODO` em:
- `references/continente_guide.md`
- `references/pingodoce_guide.md`

Abrir cada site, inspecionar elementos, e preencher os seletores CSS.

### 5. Cron Jobs

Copiar os cron jobs do scope document para a configuração do OpenClaw.

## Uso

No WhatsApp:
- "Acabou o leite" → adiciona à lista
- "Mostra a lista" → envia lista categorizada
- "Faz a triagem" → triagem manual
- "Quanto gastámos este mês?" → relatório de gastos

## Estrutura

```
grocery-manager-pt/
├── SKILL.md              # Instruções core (lido pelo agente)
├── scripts/              # Automação
│   ├── scrape_continente.py
│   ├── scrape_pingodoce.py
│   ├── price_compare.py
│   ├── consumption_tracker.py
│   └── list_optimizer.py
├── references/           # Docs carregados on-demand
│   ├── continente_guide.md
│   ├── pingodoce_guide.md
│   ├── price_comparison_logic.md
│   └── consumption_patterns.md
├── assets/templates/     # Templates de mensagens
│   ├── weekly_triage.md
│   ├── weekly_report.md
│   ├── shopping_summary.md
│   └── price_comparison.md
└── data/                 # Dados persistentes
    ├── inventory.json
    ├── shopping_history.json
    ├── consumption_model.json
    ├── family_preferences.json
    └── price_cache.json
```
