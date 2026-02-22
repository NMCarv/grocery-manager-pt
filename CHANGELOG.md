# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [0.1.0] — 2026-02-22

### Adicionado

**Skill OpenClaw**
- `SKILL.md` com 7 módulos operacionais (lista, consumo, triagem, preços, compra, WhatsApp, relatórios)
- Frontmatter com requisitos de bins, env vars e install steps
- Referências de leitura on-demand (não carregadas todas de uma vez)
- Uso de `{baseDir}` para portabilidade independente de localização de instalação

**Scripts Python**
- `scripts/price_cache.py` — gestão de cache de preços com TTL 24h, fuzzy search, parsing de preços PT
- `scripts/price_compare.py` — otimização greedy multi-mercado com cupões, saldo, threshold de entrega e rebalanceamento
- `scripts/consumption_tracker.py` — modelo de consumo com média ponderada (mais recente = maior peso), alertas de stock, feedback do utilizador
- `scripts/list_optimizer.py` — geração de lista semanal, granel e triagem com separação de itens bulk
- `scripts/setup_crons.sh` — configuração de 6 cron jobs via OpenClaw CLI

**Reference Guides (Browser Tool)**
- `references/continente_guide.md` — guia completo de automação Continente Online sem CSS selectors hardcoded
- `references/pingodoce_guide.md` — guia completo de automação Pingo Doce Online com notas do cartão Poupa
- `references/price_comparison_logic.md` — algoritmo de otimização documentado
- `references/consumption_patterns.md` — modelo de consumo e fórmulas

**Dados**
- Seed data em `data/consumption_model.json` com 18 produtos base
- Template de configuração em `data/family_preferences.json`

**Testes**
- 73 testes unitários (pytest) para os 4 scripts Python principais
- Fixtures de dados de teste em `tests/fixtures/`

**Projeto**
- Licença MIT
- `.gitignore`, `requirements.txt`, `pyproject.toml`, `conftest.py`
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`
- Templates `.github/` para issues e PRs

### Bugs Corrigidos

- `consumption_tracker.py`: `weighted_average()` atribuía incorrectamente maior peso às entradas mais antigas. Corrigido para dar maior peso às entradas mais recentes (último da lista).
- `list_optimizer.py`: `generate_triage()` falhava com `TypeError` ao comparar datetimes naive vs aware quando `next_bulk_date` era uma data simples (YYYY-MM-DD).
- `price_cache.py`: `cmd_update()` aceitava JSON que não era um objecto (ex: lista, string) e falhava em runtime. Adicionada validação de tipo.

### Arquitectura

- Browser automation usa a **browser tool nativa do OpenClaw** (snapshots + refs numerados) em vez de Playwright com seletores CSS, tornando o sistema resiliente a mudanças no layout dos sites.
- Scripts Python funcionam como utilitários de dados; a navegação é feita pelo agente LLM via browser tool.

---

## Tipos de mudança

- `Adicionado` para novas funcionalidades
- `Alterado` para mudanças em funcionalidades existentes
- `Obsoleto` para funcionalidades que serão removidas
- `Removido` para funcionalidades removidas
- `Corrigido` para correção de bugs
- `Segurança` para vulnerabilidades corrigidas
