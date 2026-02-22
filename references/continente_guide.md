# Continente Online — Guia de Automação (Browser Tool)

> Este guia descreve como o agente deve navegar e interagir com o Continente Online
> usando a browser tool do OpenClaw (snapshots + refs numerados).
> Não usa seletores CSS hardcoded — o agente identifica elementos via AI snapshot.
>
> Última verificação do fluxo: 2026-02-22
> Se um passo falhar, notificar o utilizador para verificação manual.

## URLs

| Página | URL |
|---|---|
| Homepage | `https://www.continente.pt/` |
| Login | `https://www.continente.pt/login` |
| Pesquisa | `https://www.continente.pt/pesquisa/?q={query}` |
| Carrinho | `https://www.continente.pt/carrinho` |
| Checkout | `https://www.continente.pt/checkout` |
| Cupões | `https://www.continente.pt/area-pessoal/cupoes` |
| Cartão | `https://www.continente.pt/area-pessoal/cartao-continente` |

---

## 1. Login

```
browser open "https://www.continente.pt/login"
browser snapshot
```

No snapshot, identificar:
- Campo de input para email/utilizador
- Campo de input para password
- Botão de submissão ("Entrar", "Login", "Iniciar sessão")

```
browser act type [ref_campo_email] "$CONTINENTE_EMAIL"
browser act type [ref_campo_password] "$CONTINENTE_PASSWORD"
browser act click [ref_botao_login]
```

**Verificar sucesso:** Após click, fazer novo snapshot. Sucesso se visível:
- Nome do utilizador no header
- Ícone de perfil com nome
- Redirect para a homepage

**Sessão persistente:** O browser profile `grocery` mantém cookies entre sessões. Se já estiver logado (snapshot mostra nome do utilizador no header), saltar este passo.

**2FA / verificação extra:** Se aparecer pedido de código SMS ou email → PAUSA. Notificar utilizador: "⚠️ O Continente pediu verificação adicional. Por favor verifica [email/SMS] e indica o código." Aguardar código do utilizador, introduzir, continuar.

---

## 2. Gerir Popups e Banners (Edge Cases Comuns)

Antes de qualquer interação, verificar se há popups bloqueantes:

**Banner de cookies:**
```
browser snapshot
```
Se snapshot contiver elementos com texto "Aceitar", "Gerir cookies", "Rejeitar opcionais":
- Procurar botão "Rejeitar não essenciais" ou "Aceitar apenas necessários"
- `browser act click [ref_botao_rejeitar_cookies]`

**Banner de localização / entrega:**
- Se aparecer modal a pedir localização ou zona de entrega → fechar com X ou "Continuar"

**Modal de app mobile:**
- Se aparecer popup a sugerir app → fechar com X

---

## 3. Pesquisa de Produtos

```
browser open "https://www.continente.pt/pesquisa/?q=[query_url_encoded]"
browser snapshot
```

No snapshot, identificar os cards de produto. Para cada produto relevante, extrair:

- **Nome:** Texto do título/nome do produto
- **Preço atual:** Valor numérico principal (formato "X,XX €")
- **Preço por unidade:** Texto secundário com "€/kg", "€/L", "€/un" (pode estar em fonte menor)
- **Preço anterior (riscado):** Se existir → produto está em promoção
- **Badge de promoção:** Texto como "50% na 2ª unidade", "Leve 3 pague 2", "Poupa X%"
- **Disponibilidade:** Se botão "Adicionar" está ativo ou se aparece "Esgotado"

**Estratégia de seleção do produto:**
1. Primeiro match com marca preferida da família (ver `data/family_preferences.json`)
2. Se não disponível → marca aceitável
3. Se não disponível → marca própria Continente
4. Se nada disponível → notificar família, sugerir alternativa

**Parsing de preço:**
O formato português usa vírgula como separador decimal: "2,49 €" = 2.49€.
Usar `python3 {baseDir}/scripts/price_cache.py parse-price "2,49 €"` para converter.

---

## 4. Adicionar ao Carrinho

Após identificar o produto correto no snapshot:

```
browser act click [ref_botao_adicionar]
```

Aguardar feedback visual (toast/notificação de confirmação) — fazer snapshot para confirmar.

**Ajustar quantidade** (se > 1 unidade):
- Identificar campo de quantidade ou botão "+" no carrinho
- Navegar ao carrinho, identificar o item, clicar "+" até atingir quantidade desejada
- Ou: se existir input de quantidade, usar `browser act type [ref_qty_input] "[N]"`

**Delay obrigatório:** Aguardar 2-3 segundos entre adições de produtos diferentes.

**CAPTCHA:** Se aparecer desafio CAPTCHA → PAUSA imediata. Notificar: "⚠️ O Continente apresentou um CAPTCHA. Aceder ao browser e resolver manualmente." Aguardar confirmação do utilizador antes de continuar.

---

## 5. Verificar e Ativar Cupões

```
browser open "https://www.continente.pt/area-pessoal/cupoes"
browser snapshot
```

Identificar lista de cupões disponíveis. Para cada cupão, extrair:
- Descrição (ex: "3€ de desconto em compras >50€")
- Condições: valor mínimo, categorias aplicáveis, data de validade
- Estado: ativo / por ativar

Ativar cupões relevantes para a compra atual:
```
browser act click [ref_botao_ativar_cupao]
```

Registar cupões ativados e valor total de poupança esperada.

---

## 6. Verificar Saldo do Cartão Continente

```
browser open "https://www.continente.pt/area-pessoal/cartao-continente"
browser snapshot
```

Identificar e extrair o saldo disponível. Formato esperado: "Saldo disponível: X,XX €".
Gravar valor para usar no cálculo de otimização de preços.

---

## 7. Revisão do Carrinho

```
browser open "https://www.continente.pt/carrinho"
browser snapshot
```

Verificar:
- Lista de produtos no carrinho (corresponde ao plano?)
- Total do carrinho
- Custo de entrega (grátis se >50€)

Se total difere >10% da estimativa calculada:
- PAUSA. Notificar utilizador com breakdown dos preços reais vs. estimados.
- Aguardar confirmação antes de prosseguir.

```
browser screenshot
```
Enviar screenshot ao admin para aprovação.

---

## 8. Checkout

**Só avançar após ✅ explícito do admin.**

```
browser snapshot
```
Clicar no botão "Continuar para checkout" / "Finalizar compra".

**Entrega:**
- Verificar morada pré-configurada (deve corresponder a `data/family_preferences.json`)
- Identificar grid de slots de entrega disponíveis
- Selecionar slot que corresponde às preferências: sábado ou domingo, 10h-13h
- Preferir slots gratuitos (geralmente incluídos em compras >50€)

**Pagamento:**
- Identificar métodos de pagamento guardados na conta
- Selecionar o método pré-configurado (MB Way ou cartão guardado)
- ❌ NUNCA clicar em "Adicionar novo cartão" ou introduzir dados bancários

**Cupões no checkout:**
- Verificar se existe campo de código de cupão
- Os cupões ativados anteriormente devem aparecer automaticamente
- Se não aparecerem: identificar campo e inserir códigos manualmente

**Confirmação final:**
```
browser screenshot
```
Enviar screenshot do resumo final ao admin. Mensagem: "🛒 Pronto para confirmar. Total: €[X]. Entrega: [slot]. ✅ para confirmar."

Após ✅:
```
browser act click [ref_botao_confirmar]
browser snapshot
```
Extrair número de encomenda da página de confirmação.

---

## 9. Confirmar Encomenda e Atualizar Dados

Após confirmação bem sucedida:

1. Extrair número de encomenda (formato habitual: NNN-NNNNNNN ou similar)
2. Notificar família: "✅ Encomenda Continente confirmada! Nº [X]. Entrega [slot]. Total: €[X]"
3. Gravar em `{baseDir}/data/shopping_history.json`
4. Executar tracker de consumo com os dados da compra

---

## Comportamento em Caso de Falha

| Situação | Ação |
|---|---|
| Seletor / elemento não encontrado | Tentar novamente após snapshot fresco; se persistir → notificar |
| Produto esgotado | Notificar família, sugerir produto alternativo, aguardar resposta |
| Preço mudou no carrinho | Notificar diff, aguardar aprovação |
| Sessão expirada | Re-login (máx 2 tentativas automáticas) |
| CAPTCHA | PAUSA, escalar ao utilizador |
| Bloqueio detetado (erro 429 / bot detection) | Cooldown 24h, notificar utilizador |
| Site em manutenção | Notificar, tentar novamente após 2h |
| Timeout (página não carrega >30s) | Retry 1x, depois notificar |
