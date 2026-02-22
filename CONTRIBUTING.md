# Contribuir para o Grocery Manager PT

Obrigado pelo interesse em contribuir! Este documento explica como participar no projeto.

---

## Índice

- [Setup do ambiente](#setup-do-ambiente)
- [Como contribuir](#como-contribuir)
- [Adicionar um novo supermercado](#adicionar-um-novo-supermercado)
- [Estilo de código](#estilo-de-código)
- [Testes](#testes)
- [Submeter um pull request](#submeter-um-pull-request)
- [Reportar bugs](#reportar-bugs)
- [Sugerir funcionalidades](#sugerir-funcionalidades)

---

## Setup do ambiente

```bash
# 1. Fork o repositório e clona localmente
git clone https://github.com/nmcarv/grocery-manager-pt.git
cd grocery-manager-pt

# 2. Cria um branch para a tua alteração
git checkout -b feat/nome-da-funcionalidade

# 3. Instala as dependências
pip install -r requirements.txt

# 4. Verifica que os testes passam
python -m pytest tests/ -v
```

Não é necessário ter o OpenClaw instalado para desenvolver os scripts Python ou escrever testes. O OpenClaw só é necessário para testar a skill end-to-end.

---

## Como contribuir

### O que é bem-vindo

- **Novos supermercados** — Auchan, El Corte Inglés, Mercadão, Lidl (quando tiver online robusto)
- **Melhorias aos algoritmos** — otimização de preços, modelo de consumo, geração de lista
- **Melhorias aos guides de referência** — seletores atualizados, novos edge cases documentados
- **Testes** — aumentar cobertura, testes de integração
- **Traduções** — adaptar para outros países (Espanha, Brasil) com os seus supermercados
- **Correção de bugs** — ver [issues abertas](https://github.com/nmcarv/grocery-manager-pt/issues)
- **Documentação** — melhorar guides de referência, exemplos de configuração

### O que NÃO fazer

- Não commitar credenciais, tokens ou dados pessoais
- Não hardcodar seletores CSS nos scripts Python (pertencem aos guides de referência em `references/`)
- Não alterar `data/*.json` com dados pessoais — estes ficheiros são templates de exemplo
- Não adicionar dependências pesadas sem discussão prévia (issue)

---

## Adicionar um novo supermercado

Para adicionar suporte a um novo supermercado, é necessário:

### 1. Criar o guide de referência

Criar `references/NOME_guide.md` seguindo a estrutura de `references/continente_guide.md`:

```markdown
# NOME Online — Guia de Automação (Browser Tool)

## URLs

## 1. Login

## 2. Gerir Popups

## 3. Pesquisa de Produtos

## 4. Adicionar ao Carrinho

## 5. Verificar Cupões / Saldo

## 6. Revisão e Aprovação

## 7. Checkout

## Comportamento em Caso de Falha
```

**Importante:** Não usar seletores CSS hardcoded. Descrever os elementos em linguagem natural para o agente identificar via browser snapshot.

### 2. Adicionar ao SKILL.md

Em `SKILL.md`, na tabela de Scripts e na secção de Referências, adicionar entradas para o novo supermercado.

Actualizar a descrição no frontmatter YAML para incluir o novo supermercado nos triggers de activação.

### 3. Registar em config.py

`scripts/config.py` é a **única fonte de verdade** para integrações de mercado.
Todos os outros scripts (`price_cache`, `price_compare`, `list_optimizer`) importam daqui.

```python
# scripts/config.py

class OnlineMarket(str, Enum):
    CONTINENTE = "continente"
    PINGODOCE = "pingodoce"
    NOVO_SUPERMERCADO = "novo_supermercado"   # ← adicionar aqui

DELIVERY_CONFIG = {
    ...
    "novo_supermercado": {
        "cost": 2.50,
        "free_threshold": 60.0,
        "min_order": 20.0,
    },
}
```

**Não** editar `MARKETS` em `price_cache.py` nem `price_compare.py` — esses valores são agora derivados automaticamente do enum.

### 4. Adicionar variáveis de ambiente ao SKILL.md

No frontmatter de `SKILL.md`:

```yaml
metadata:
  openclaw:
    requires:
      env:
        - NOVO_SUPERMERCADO_EMAIL
        - NOVO_SUPERMERCADO_PASSWORD
```

### 5. Escrever testes

Adicionar testes em `tests/test_price_compare.py` para o novo mercado (delivery thresholds, etc.).

---

## Estilo de código

- **Python 3.11+** — usar type hints onde útil
- **Sem formatter obrigatório** por agora — seguir o estilo existente (4 espaços, nomes descritivos)
- **Docstrings** em português nos scripts (o projeto é PT-focused), inglês nas assinaturas de tipo
- **Ficheiros de dados** (`.json`) em português
- **Commits** em português ou inglês — ser descritivo (ex: `fix: corrigir cálculo de média ponderada em weighted_average`)

### Mensagens de commit

Seguir o formato [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: adicionar suporte a Auchan Online
fix: corrigir parsing de preço com separador de milhar
docs: atualizar guide do Pingo Doce com novos seletores
test: adicionar testes para apply_coupons com categorias
refactor: simplificar lógica de fuzzy search no price_cache
```

---

## Testes

Todos os PRs devem incluir testes para o código novo. Para correr:

```bash
# Todos os testes
python -m pytest tests/ -v

# Apenas um ficheiro
python -m pytest tests/test_price_compare.py -v

# Com coverage (se tiveres pytest-cov instalado)
python -m pytest tests/ --cov=scripts --cov-report=term-missing
```

Os scripts em `scripts/` podem ser testados directamente:

```bash
python scripts/price_compare.py
python scripts/consumption_tracker.py check-stock
python scripts/list_optimizer.py triage --next-bulk-date 2026-03-01
python scripts/price_cache.py stats
```

---

## Submeter um pull request

1. **Fork** o repositório
2. **Cria um branch** descritivo: `git checkout -b feat/auchan-support`
3. **Faz as alterações** — commits pequenos e focados
4. **Corre os testes**: `python -m pytest tests/ -v` — todos devem passar
5. **Abre o PR** com o template fornecido, descrevendo:
   - O problema que resolve ou funcionalidade que adiciona
   - Como testar as alterações
   - Screenshots ou exemplos de output, se aplicável
6. **Aguarda review** — os maintainers irão responder em alguns dias

PRs que quebrem testes existentes sem justificação não serão aceites.

---

## Reportar bugs

Usar o [template de bug report](.github/ISSUE_TEMPLATE/bug_report.md) em Issues.

Incluir sempre:

- Versão do Python e OpenClaw
- Passos para reproduzir
- Comportamento esperado vs. actual
- Output de erro (sem credenciais ou dados pessoais)

Para problemas de segurança, **não** abrir uma issue pública — ver [SECURITY.md](SECURITY.md).

---

## Sugerir funcionalidades

Usar o [template de feature request](.github/ISSUE_TEMPLATE/feature_request.md) em Issues.

Antes de submeter, verificar se já existe uma issue similar (aberta ou fechada).
