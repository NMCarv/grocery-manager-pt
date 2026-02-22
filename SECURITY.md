# Política de Segurança

## Âmbito

Este projeto interage com:

- Contas em supermercados online (Continente, Pingo Doce)
- Credenciais de login guardadas via OpenClaw
- Execução de compras online com aprovação via WhatsApp

Tomamos a segurança a sério. Esta página descreve o que o projeto faz para proteger os utilizadores e como reportar vulnerabilidades.

## Garantias de Segurança do Bot

### O bot NUNCA irá:

- **Introduzir dados bancários** — o checkout usa apenas métodos de pagamento pré-guardados nas contas dos supermercados. Nenhum campo de cartão de crédito é alguma vez preenchido pelo agente.
- **Executar uma compra sem aprovação** — todos os checkouts requerem um ✅ explícito do utilizador admin no WhatsApp. O bot para e aguarda, independentemente do timeout.
- **Ultrapassar o budget configurado** — compras acima de `weekly_limit_eur` ou `monthly_limit_eur` são recusadas automaticamente (requer override explícito).
- **Guardar credenciais em ficheiros** — todas as credenciais são injectadas pelo OpenClaw em runtime via variáveis de ambiente; nunca aparecem em logs, mensagens ou ficheiros da skill.
- **Partilhar credenciais em mensagens** — o agente nunca inclui passwords, tokens ou dados sensíveis em mensagens WhatsApp ou outros canais.
- **Resolver CAPTCHAs automaticamente** — quando um CAPTCHA aparece, o bot pára e notifica o utilizador para resolução manual.

### O bot PODE (com aprovação):

- Navegar em sites de supermercados autenticado
- Adicionar produtos ao carrinho
- Activar cupões e usar saldo de cartões de fidelização
- Seleccionar slots de entrega
- Confirmar encomendas após aprovação explícita

## Configuração Segura Recomendada

Antes de ligar o bot a contas reais, estas práticas limitam significativamente a exposição em caso de comportamento inesperado ou comprometimento de credenciais.

### 1. Princípio do Mínimo Privilégio

O bot apenas precisa de:

- Fazer login numa conta de supermercado
- Pesquisar produtos e adicionar ao carrinho
- Activar cupões pré-carregados e usar saldo de fidelização
- Confirmar o checkout com um método de pagamento **já guardado** na conta

Não precisa de — e não deve ter — acesso a:

- Contas bancárias ou cartões principais
- Contas de supermercado com histórico de compras pessoal
- Permissões de administrador em nenhuma plataforma

### 2. Contas Dedicadas nos Supermercados

Cria uma conta separada em cada supermercado **exclusivamente** para o bot:

| O que fazer                                   | Porquê                                                                                           |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Email dedicado (ex: `compras-bot@gmail.com`)  | Isola o acesso; se as credenciais vierem a ser comprometidas, o teu email pessoal não é afectado |
| Password única, nunca reutilizada             | Evita que um eventual leak comprometa outras contas                                              |
| **Não** migrar o histórico de compras pessoal | A conta nova começa limpa — sem dados pessoais acumulados                                        |
| Activar 2FA                                   | O bot pára e notifica quando aparece 2FA — o código chega ao teu telemóvel, não ao bot           |

### 3. Método de Pagamento Limitado (MB Way)

Em vez de ligar um cartão de débito/crédito principal, usa o **MB Way** para criar um cartão virtual com limite por comerciante:

1. Abre o MB Way → **Cartões** → **Criar cartão**
2. Associa o cartão a um comerciante específico (Continente ou Pingo Doce)
3. Define um **limite mensal** próximo do teu orçamento configurado (ex: `monthly_limit_eur: 500` → cartão com limite €550)
4. Guarda este cartão na conta do supermercado **antes** de activar o bot
5. Repete para cada supermercado

O bot usa exclusivamente métodos de pagamento pré-guardados — nunca introduz dados de cartão. O limite do cartão MB Way garante que, mesmo que algo corra mal, o dano financeiro é limitado e reversível.

### 4. Progressão Gradual de Permissões

Não actives tudo de uma vez. Segue uma progressão de confiança:

**Fase 1 — Observação (semanas 1–2)**
Deixa o bot gerar listas e comparar preços. Não aprovares nenhum ✅. Verifica se:

- As previsões de consumo fazem sentido
- Os preços no cache correspondem aos reais
- As listas semanal e granel estão correctas

**Fase 2 — Aprovação do carrinho (semanas 3–4)**
Começa a aprovar carrinhos mas **cancela antes do checkout**. Verifica se:

- Os produtos seleccionados são os correctos
- As quantidades e marcas correspondem às preferências
- O total estimado está dentro do budget

**Fase 3 — Compras pequenas (mês 2)**
Aprova checkouts para compras inferiores a €30. Verifica se:

- As encomendas são confirmadas correctamente
- O número de encomenda é registado em `shopping_history.json`
- A entrega chega com os produtos esperados

**Fase 4 — Operação normal**
Após confiança estabelecida, usa o bot com o budget completo configurado.

## Credenciais e Segredos

As credenciais dos supermercados são configuradas via OpenClaw:

```bash
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_EMAIL "..."
openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_PASSWORD "..."
```

Estas ficam guardadas em `~/.openclaw/openclaw.json` (na máquina do utilizador, não no repositório). Ver a [documentação do OpenClaw](https://docs.openclaw.ai) sobre como o OpenClaw protege secrets em runtime.

**Importante:** Nunca commitar ficheiros `.env`, `openclaw.json` ou qualquer ficheiro com credenciais. O `.gitignore` já exclui estes ficheiros.

## Dados Persistentes

Os ficheiros em `data/` podem conter informação sensível:

| Ficheiro                  | Dados sensíveis potenciais           |
| ------------------------- | ------------------------------------ |
| `family_preferences.json` | Morada de entrega, nomes dos membros |
| `shopping_history.json`   | Histórico de compras e preços pagos  |
| `consumption_model.json`  | Padrões de consumo da família        |

**Recomendações:**

- Não commitar `data/` com dados reais para repositórios públicos (o `.gitignore` não exclui `data/` por omissão — adicionar se necessário)
- Em ambientes partilhados, garantir que `~/.openclaw/` tem permissões de leitura restritas

## Reportar uma Vulnerabilidade

**Não abrir uma issue pública** para vulnerabilidades de segurança.

Para reportar uma vulnerabilidade:

1. Enviar um email para **[security@SEU_DOMINIO — atualizar antes de publicar]** com:
   - Descrição da vulnerabilidade
   - Passos para reproduzir
   - Impacto potencial
   - Sugestão de mitigação (opcional)

2. Iremos responder em **72 horas** com confirmação de recepção.

3. Trabalharemos contigo para validar e corrigir a vulnerabilidade antes de qualquer divulgação pública.

4. Após a correção, publicamos um advisory (CVE se aplicável) e reconhecemos a tua contribuição, se assim desejares.

**Nota:** Este projeto não tem um programa de bug bounty.

## Versões Suportadas

Apenas a versão mais recente do `main` branch recebe patches de segurança.

## Desactivar o Bot em Emergência

Se o bot estiver a comportar-se de forma inesperada:

```bash
# Parar todos os cron jobs
openclaw cron list
openclaw cron remove <job-id>  # para cada job

# Revogar acesso à skill
openclaw config set skills.entries.grocery-manager-pt.enabled false
```

Para cancelar uma encomenda já efectuada, contactar directamente o supermercado através do seu site ou linha de apoio ao cliente.
