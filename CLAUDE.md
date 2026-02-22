@AGENTS.md

# Notas específicas para Claude Code

O ficheiro acima (`AGENTS.md`) contém o contexto completo do projecto — arquitectura,
comandos, convenções, modelo de dados e regras para agentes. Lê-o na íntegra antes de
fazer qualquer alteração.

## Comandos rápidos

```bash
python -m pytest tests/ -v          # verificar antes de qualquer commit
python -m pytest tests/ -q          # output compacto para validação rápida
python scripts/price_cache.py stats # estado do cache de preços
python scripts/consumption_tracker.py check-stock  # alertas de stock
```

## Preferências de trabalho

- **Ferramentas de ficheiros** em vez de bash sempre que possível (Read, Edit, Write, Grep, Glob)
- **Bash** apenas para `git`, `pytest`, e comandos de sistema
- Antes de editar qualquer ficheiro Python, ler o ficheiro completo para ter contexto
- Ao adicionar funcionalidade nova, sempre verificar se existem testes a actualizar

## Contexto do SKILL.md vs. scripts/

`SKILL.md` contém instruções para o **agente OpenClaw em produção** (o que o bot faz
quando a família envia mensagens). Os scripts em `scripts/` são **utilitários chamados
por esse agente** — não implementam comportamento do agente directamente.

Quando alteras `SKILL.md`, estás a mudar o comportamento do bot em produção.
Quando alteras `scripts/`, estás a mudar a lógica de dados que o bot usa.

## Ficheiros sensíveis — não modificar sem contexto

| Ficheiro                                                | Porquê é sensível                                                                      |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `scripts/consumption_tracker.py` → `weighted_average()` | Lógica de peso foi corrigida de um bug (mais recente = maior peso = ÚLTIMO da lista)   |
| `scripts/list_optimizer.py` → `generate_triage()`       | Comparação de datas deve usar `datetime.now()` naive, não `datetime.now(timezone.utc)` |
| `data/family_preferences.example.json`                  | Template commitado — copiar para `family_preferences.json` (gitignored) localmente     |
| `SKILL.md` → caminhos                                   | Usar sempre `{baseDir}/...`, nunca caminhos absolutos ou relativos hardcoded           |

## Ao fazer commit

Seguir Conventional Commits (ver `AGENTS.md`). Não commitar:

- Ficheiros `data/` com dados pessoais reais
- `.env` ou qualquer ficheiro com credenciais
- `CLAUDE.local.md` (se existir — é pessoal e está no `.gitignore`)
