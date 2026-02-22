#!/usr/bin/env bash
# =============================================================================
# Grocery Manager PT — Setup de Cron Jobs no OpenClaw
#
# Executa este script uma vez para configurar todos os cron jobs automáticos.
# Para re-configurar: remover jobs existentes primeiro com `openclaw cron list`
# e `openclaw cron remove <id>`, depois correr este script novamente.
#
# Uso:
#   chmod +x scripts/setup_crons.sh
#   ./scripts/setup_crons.sh
#
# Pré-requisito: OpenClaw instalado e Gateway ativo.
# =============================================================================

set -euo pipefail

# Configuração do canal WhatsApp (alterar para o número/grupo correto)
WHATSAPP_TO="${GROCERY_WHATSAPP_GROUP:-}"

if [ -z "$WHATSAPP_TO" ]; then
  echo "⚠️  GROCERY_WHATSAPP_GROUP não definida."
  echo "   Define a variável de ambiente com o ID do grupo WhatsApp antes de correr:"
  echo "   export GROCERY_WHATSAPP_GROUP='120363000000000000@g.us'"
  echo ""
  echo "   O ID do grupo pode ser obtido com: openclaw channels whatsapp groups"
  echo ""
  read -p "Continuar mesmo assim? Os jobs serão criados sem entrega WhatsApp. (y/N) " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

echo "🛒 Configurando cron jobs do Grocery Manager PT..."
echo ""

# ---------------------------------------------------------------------------
# 1. Stock Check Diário (10h, todos os dias)
# ---------------------------------------------------------------------------
echo "📦 1/6 — daily-stock-check (10h diário)"
openclaw cron add \
  --name "grocery-daily-stock-check" \
  --cron "0 10 * * *" \
  --tz "Europe/Lisbon" \
  --session isolated \
  --message "Executa stock check diário: corre '{baseDir}/.venv/bin/python3 {baseDir}/scripts/consumption_tracker.py check-stock'. Se houver alertas (produtos com ≤2 dias de stock), notifica a família. Se tudo OK, não envies mensagem." \
  --announce \
  --channel whatsapp \
  ${WHATSAPP_TO:+--to "$WHATSAPP_TO"}

echo "  ✅ Criado"

# ---------------------------------------------------------------------------
# 2. Triagem Semanal (domingo 9h)
# ---------------------------------------------------------------------------
echo "🗓️  2/6 — weekly-triage (domingo 9h)"
openclaw cron add \
  --name "grocery-weekly-triage" \
  --cron "0 9 * * 0" \
  --tz "Europe/Lisbon" \
  --session isolated \
  --message "Executa triagem semanal completa: (1) lê family_preferences.json para obter next_bulk_date, (2) corre '{baseDir}/.venv/bin/python3 {baseDir}/scripts/list_optimizer.py triage --next-bulk-date [DATA]', (3) compara preços em cache e atualiza se necessário, (4) formata proposta usando template em {baseDir}/assets/templates/weekly_triage.md, (5) envia ao grupo familiar via WhatsApp, (6) aguarda aprovação durante 4h." \
  --announce \
  --channel whatsapp \
  ${WHATSAPP_TO:+--to "$WHATSAPP_TO"}

echo "  ✅ Criado"

# ---------------------------------------------------------------------------
# 3. Planeamento Mensal de Granel (dia 25, 9h)
# ---------------------------------------------------------------------------
echo "📦 3/6 — monthly-bulk-planning (dia 25, 9h)"
openclaw cron add \
  --name "grocery-monthly-bulk-planning" \
  --cron "0 9 25 * *" \
  --tz "Europe/Lisbon" \
  --session isolated \
  --message "Planeia compra a granel do mês seguinte: (1) corre '{baseDir}/.venv/bin/python3 {baseDir}/scripts/list_optimizer.py bulk', (2) compara preços bulk entre Continente e Pingo Doce, (3) gera proposta para os próximos 30 dias, (4) envia ao grupo familiar para aprovação, (5) atualiza next_bulk_date em family_preferences.json." \
  --announce \
  --channel whatsapp \
  ${WHATSAPP_TO:+--to "$WHATSAPP_TO"}

echo "  ✅ Criado"

# ---------------------------------------------------------------------------
# 4. Relatório Semanal (segunda 8h)
# ---------------------------------------------------------------------------
echo "📊 4/6 — weekly-report (segunda 8h)"
openclaw cron add \
  --name "grocery-weekly-report" \
  --cron "0 8 * * 1" \
  --tz "Europe/Lisbon" \
  --session isolated \
  --message "Gera relatório semanal de compras: lê shopping_history.json para a semana passada, calcula totais por mercado e categoria, poupança gerada, cupões usados. Formata usando template {baseDir}/assets/templates/weekly_report.md e envia ao grupo familiar." \
  --announce \
  --channel whatsapp \
  ${WHATSAPP_TO:+--to "$WHATSAPP_TO"}

echo "  ✅ Criado"

# ---------------------------------------------------------------------------
# 5. Relatório Mensal (dia 1, 9h)
# ---------------------------------------------------------------------------
echo "📊 5/6 — monthly-report (dia 1, 9h)"
openclaw cron add \
  --name "grocery-monthly-report" \
  --cron "0 9 1 * *" \
  --tz "Europe/Lisbon" \
  --session isolated \
  --message "Gera relatório mensal completo de compras: lê shopping_history.json para o mês anterior, calcula média semanal, breakdown por categoria (%), poupança total acumulada, tendências de preço dos produtos mais comprados (subidas/descidas >5%). Formata e envia ao grupo familiar." \
  --announce \
  --channel whatsapp \
  ${WHATSAPP_TO:+--to "$WHATSAPP_TO"}

echo "  ✅ Criado"

# ---------------------------------------------------------------------------
# 6. Refresh de Cache de Preços (quarta e sábado, 6h) — sem entrega
# ---------------------------------------------------------------------------
echo "💰 6/6 — price-cache-refresh (quarta e sábado, 6h)"
openclaw cron add \
  --name "grocery-price-cache-refresh" \
  --cron "0 6 * * 3,6" \
  --tz "Europe/Lisbon" \
  --session isolated \
  --message "Atualiza cache de preços: (1) corre '{baseDir}/.venv/bin/python3 {baseDir}/scripts/price_cache.py expired' para listar entradas expiradas, (2) usa browser tool para pesquisar preços atualizados dos 20 produtos mais frequentes em consumption_model.json no Continente e Pingo Doce, (3) atualiza price_cache.json via '{baseDir}/.venv/bin/python3 {baseDir}/scripts/price_cache.py update ...', (4) se algum produto subiu >10%, registar para relatório semanal. Não enviar mensagem a menos que encontre variação significativa."

echo "  ✅ Criado (sem entrega WhatsApp — apenas interno)"

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
echo ""
echo "✅ Todos os cron jobs configurados com sucesso!"
echo ""
echo "Para verificar:"
echo "  openclaw cron list"
echo ""
echo "Para testar um job manualmente:"
echo "  openclaw cron run <job-id>"
echo ""
echo "⚠️  Lembra-te de:"
echo "  1. Configurar GROCERY_WHATSAPP_GROUP com o ID do grupo familiar"
echo "  2. Adicionar credenciais: openclaw config set skills.entries.grocery-manager-pt.env.CONTINENTE_EMAIL '...'"
echo "  3. Configurar morada em data/family_preferences.json"
