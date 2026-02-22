# 🛒 Grocery Manager PT

Skill OpenClaw para gestão completa de compras de mercearia em Portugal.

Família de 7 pessoas. Supermercados: Continente Online + Pingo Doce Online.
Coordenação via grupo WhatsApp. Automação via browser tool nativa do OpenClaw.

## Setup Rápido

### 1. Credenciais

```bash
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_EMAIL "email@example.com"
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_PASSWORD "password"
openclaw config set skills.entries.grocery-manager-pt.env.PINGODOCE_EMAIL "email@example.com"
openclaw config set skills.entries.grocery-manager-pt.env.PINGODOCE_PASSWORD "password"
```

### 2. Dependências Python

```bash
pip3 install -r requirements.txt
```

### 3. Configuração da Família

Editar `data/family_preferences.json`:
- Morada de entrega (campo `address`)
- Nomes dos membros da família
- Budget semanal/mensal
- Dias e horários preferidos de entrega

### 4. Cron Jobs

```bash
# Definir o ID do grupo WhatsApp
export GROCERY_WHATSAPP_GROUP="120363000000000000@g.us"

# Obter ID do grupo:
# openclaw channels whatsapp groups

chmod +x scripts/setup_crons.sh
./scripts/setup_crons.sh
```

### 5. Browser Profile

O agente usa a browser tool nativa do OpenClaw com o profile `grocery` para manter
as sessões dos supermercados isoladas. Não é necessária configuração adicional —
o OpenClaw gere o profile automaticamente.

---

## Uso (via WhatsApp)

| Mensagem | Resultado |
|---|---|
| "Acabou o leite" | Adiciona à lista |
| "Precisamos de 3kg de frango" | Adiciona com quantidade |
| "Mostra a lista" | Lista categorizada |
| "Faz a triagem" | Triagem manual |
| "Quanto gastámos este mês?" | Relatório de gastos |
| ✅ (resposta a proposta) | Aprova compra |

---

## Estrutura

```
grocery-manager-pt/
├── SKILL.md                      # Instruções core do agente
├── requirements.txt              # Dependências Python
├── scripts/
│   ├── price_cache.py            # Cache de preços (leitura/escrita pelo agente)
│   ├── price_compare.py          # Otimização multi-mercado
│   ├── consumption_tracker.py    # Modelo de consumo e alertas
│   ├── list_optimizer.py         # Geração de lista semanal/granel
│   └── setup_crons.sh            # Configuração de cron jobs
├── references/
│   ├── continente_guide.md       # Guia de automação Continente (browser tool)
│   ├── pingodoce_guide.md        # Guia de automação Pingo Doce (browser tool)
│   ├── price_comparison_logic.md # Algoritmo de otimização
│   └── consumption_patterns.md   # Modelo de consumo
├── assets/templates/             # Templates de mensagens WhatsApp
│   ├── weekly_triage.md
│   ├── weekly_report.md
│   ├── shopping_summary.md
│   └── price_comparison.md
├── data/                         # Dados persistentes (editáveis)
│   ├── inventory.json            # Lista de compras + inventário
│   ├── shopping_history.json     # Histórico de compras
│   ├── consumption_model.json    # Modelo de consumo (seed: 18 produtos base)
│   ├── family_preferences.json   # Preferências, budget, membros
│   └── price_cache.json          # Cache de preços (TTL 24h)
└── tests/                        # Testes unitários
    ├── test_price_cache.py
    ├── test_price_compare.py
    ├── test_consumption_tracker.py
    ├── test_list_optimizer.py
    └── fixtures/                 # Dados de teste
```

---

## Testes

```bash
python3 -m pytest tests/ -v
```

73 testes unitários para os scripts Python principais.

---

## Cron Jobs Configurados

| Job | Schedule | Ação |
|---|---|---|
| `grocery-daily-stock-check` | Diário 10h | Alerta se produto acaba em ≤2 dias |
| `grocery-weekly-triage` | Domingo 9h | Triagem + proposta de compra |
| `grocery-monthly-bulk-planning` | Dia 25 9h | Planeamento granel mensal |
| `grocery-weekly-report` | Segunda 8h | Relatório semanal de gastos |
| `grocery-monthly-report` | Dia 1 9h | Relatório mensal completo |
| `grocery-price-cache-refresh` | Quarta e sábado 6h | Refresh de preços |

---

## Arquitetura de Browser Automation

O agente usa a **browser tool nativa do OpenClaw** (não Playwright):

1. `browser open <url>` — navegar para página
2. `browser snapshot` — obter árvore de UI com refs numerados
3. `browser act click <ref>` / `browser act type <ref> "texto"` — interagir
4. `browser screenshot` — captura para aprovação

Vantagem: sem seletores CSS hardcoded. O agente identifica elementos visualmente,
adaptando-se automaticamente a mudanças no layout dos sites.

Consultar `references/continente_guide.md` e `references/pingodoce_guide.md`
para os fluxos detalhados de navegação.

---

## Segurança

- Credenciais apenas em env vars (nunca em ficheiros)
- ❌ O agente nunca introduz dados bancários
- ✅ Toda compra requer aprovação explícita do admin (Nuno) no WhatsApp
- Budget configurável com recusa automática de compras acima do limite
- Browser profile `grocery` isolado do browser pessoal
