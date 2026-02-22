# Continente Online — Browser Automation Guide

> ⚠️ Este ficheiro deve ser mantido manualmente. Sites de supermercado mudam frequentemente.
> Última verificação: YYYY-MM-DD
> Se um seletor falhar, notifica o utilizador para atualização deste guide.

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

## Fluxo de Login

1. Navegar a `/login`
2. Preencher campo email: `[SELETOR: input#email ou similar]`
3. Preencher campo password: `[SELETOR: input#password ou similar]`
4. Clicar botão login: `[SELETOR: button[type=submit] ou similar]`
5. Verificar sucesso: presença de nome do utilizador no header ou redirect para homepage
6. Se 2FA solicitado → PAUSA → notificar utilizador

**Nota:** Manter sessão ativa reutilizando browser profile `grocery`. Cookies persistem entre sessões.

## Pesquisa de Produtos

1. Navegar a `/pesquisa/?q={query}` (URL encode da query)
2. Aguardar carregamento dos resultados: `[SELETOR: .product-list ou similar]`
3. Para cada resultado extrair:
   - Nome do produto: `[SELETOR]`
   - Preço atual: `[SELETOR]` (atenção: preço pode estar em formato "X,XX €")
   - Preço por unidade (€/kg, €/L): `[SELETOR]`
   - Preço anterior (se em promoção): `[SELETOR]`
   - Badge de promoção: `[SELETOR]`
   - Disponibilidade: `[SELETOR]`
   - Botão adicionar ao carrinho: `[SELETOR]`

**Parsing de preço:**
- Formato PT: "2,49 €" → float 2.49
- Preço por kg/L pode estar em texto pequeno abaixo do preço principal
- Promoções podem mostrar dois preços (riscado + novo)

## Adicionar ao Carrinho

1. Clicar botão "Adicionar" no produto desejado
2. Se quantidade > 1: usar seletor de quantidade `[SELETOR]` ou clicar "+" N vezes
3. Verificar toast/feedback de confirmação
4. Delay de 2s entre adições (evitar rate limit)

## Verificar Cupões

1. Navegar a `/area-pessoal/cupoes`
2. Listar cupões disponíveis: `[SELETOR: .coupon-list ou similar]`
3. Para cada cupão extrair:
   - Descrição (e.g., "3€ em compras superiores a 50€")
   - Condições (valor mínimo, categorias, validade)
   - Estado (ativo/por ativar)
4. Ativar cupões relevantes: clicar botão ativar `[SELETOR]`

## Verificar Saldo do Cartão

1. Navegar a `/area-pessoal/cartao-continente`
2. Extrair saldo disponível: `[SELETOR]`
3. Formato esperado: "Saldo: X,XX €"

## Checkout

1. Navegar a `/carrinho` → verificar total
2. Clicar "Continuar para checkout" `[SELETOR]`
3. **Entrega:**
   - Verificar morada pré-selecionada
   - Selecionar slot: `[SELETOR: calendário de slots]`
   - Preferir slots gratuitos (compras >50€ geralmente)
4. **Pagamento:**
   - Selecionar método pré-guardado (NUNCA introduzir dados novos)
   - Se MBWay disponível e preferido → selecionar
5. **Cupões:**
   - Verificar campo de código de cupão: `[SELETOR]`
   - Aplicar cupões ativos
6. **PAUSA** → Screenshot do resumo final → enviar para aprovação
7. Após ✅ → clicar confirmar `[SELETOR]`
8. Extrair número de encomenda da página de confirmação

## Edge Cases

- **Popup de cookies:** Aceitar mínimos (rejeitar marketing) → `[SELETOR]`
- **Banner de localização:** Fechar → `[SELETOR]`
- **Modal de app:** Fechar → `[SELETOR]`
- **Produto esgotado:** Texto "Esgotado" ou botão desativado → skip, notificar
- **Preço diferente no carrinho:** Pode acontecer se promoção expirou entre pesquisa e adição
- **Sessão expirada:** Re-login automático (max 2 tentativas)
- **Timeout:** Se página não carrega em 30s → retry 1x → fallback: notificar

## Seletores

> 🔴 **PREENCHER NA PRIMEIRA CONFIGURAÇÃO**
> Abrir Continente Online, inspecionar elementos, e preencher os seletores abaixo.
> Usar seletores estáveis: IDs > data-attributes > classes semânticas > posição.

```yaml
selectors:
  login:
    email_input: "TODO"
    password_input: "TODO"
    submit_button: "TODO"
    success_indicator: "TODO"
  search:
    results_container: "TODO"
    product_card: "TODO"
    product_name: "TODO"
    product_price: "TODO"
    product_unit_price: "TODO"
    product_old_price: "TODO"
    product_promo_badge: "TODO"
    product_availability: "TODO"
    add_to_cart_button: "TODO"
  cart:
    cart_total: "TODO"
    checkout_button: "TODO"
    quantity_input: "TODO"
  coupons:
    coupon_list: "TODO"
    coupon_description: "TODO"
    coupon_activate_button: "TODO"
  checkout:
    delivery_slots: "TODO"
    payment_methods: "TODO"
    confirm_button: "TODO"
    order_number: "TODO"
  common:
    cookie_accept_minimal: "TODO"
    close_popup: "TODO"
    user_name_header: "TODO"
```
