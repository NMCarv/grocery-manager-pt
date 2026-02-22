# Pingo Doce Online — Browser Automation Guide

> ⚠️ Este ficheiro deve ser mantido manualmente. Sites de supermercado mudam frequentemente.
> Última verificação: YYYY-MM-DD
> Se um seletor falhar, notifica o utilizador para atualização deste guide.

## URLs

| Página | URL |
|---|---|
| Homepage | `https://www.pingodoce.pt/` |
| Login | `https://www.pingodoce.pt/login/` |
| Pesquisa | `https://www.pingodoce.pt/pesquisa/?q={query}` |
| Carrinho | `https://www.pingodoce.pt/carrinho/` |
| Checkout | `https://www.pingodoce.pt/checkout/` |
| Poupa | `https://www.pingodoce.pt/area-cliente/poupa/` |
| Cupões | `https://www.pingodoce.pt/area-cliente/cupoes/` |

## Fluxo de Login

1. Navegar a `/login/`
2. Preencher campo email: `[SELETOR: TODO]`
3. Preencher campo password: `[SELETOR: TODO]`
4. Clicar botão login: `[SELETOR: TODO]`
5. Verificar sucesso: presença de nome/área cliente
6. Se 2FA ou verificação extra → PAUSA → notificar utilizador

## Pesquisa de Produtos

1. Navegar a `/pesquisa/?q={query}`
2. Aguardar resultados: `[SELETOR: TODO]`
3. Para cada resultado extrair:
   - Nome do produto: `[SELETOR: TODO]`
   - Preço atual: `[SELETOR: TODO]`
   - Preço por unidade: `[SELETOR: TODO]`
   - Preço anterior (se promoção): `[SELETOR: TODO]`
   - Promoção (e.g., "Poupa 30%"): `[SELETOR: TODO]`
   - Disponibilidade: `[SELETOR: TODO]`
   - Botão adicionar: `[SELETOR: TODO]`

**Notas específicas Pingo Doce:**
- O Pingo Doce usa o cartão "Poupa" como sistema de descontos
- Preços Poupa são visíveis apenas quando logado
- Algumas promoções são "cupão digital" que precisa ativação prévia

## Adicionar ao Carrinho

1. Clicar "Adicionar" no produto
2. Ajustar quantidade se necessário
3. Verificar feedback visual
4. Delay de 2s entre adições

## Verificar Cupões e Saldo Poupa

1. Navegar a `/area-cliente/cupoes/`
2. Listar cupões disponíveis com descrição e condições
3. Ativar cupões relevantes para a compra
4. Navegar a `/area-cliente/poupa/`
5. Extrair saldo Poupa: `[SELETOR: TODO]`

## Checkout

1. Navegar ao carrinho → verificar total
2. Prosseguir para checkout
3. **Entrega:**
   - Confirmar morada
   - Selecionar slot de entrega
   - Verificar custo de entrega (grátis acima de certo valor?)
4. **Pagamento:**
   - Selecionar método pré-guardado
   - Aplicar saldo Poupa se disponível
5. **PAUSA** → Screenshot → aprovação do admin
6. Após ✅ → confirmar encomenda
7. Extrair número de encomenda

## Edge Cases

- **Popup de cookies:** Rejeitar opcionais → `[SELETOR: TODO]`
- **Seleção de loja:** Pingo Doce pode pedir selecionar loja para delivery → `[SELETOR: TODO]`
- **Produto indisponível na zona:** Pode estar listado mas não entregável
- **Mínimo de encomenda:** Verificar se existe valor mínimo para entrega
- **Sessão expirada:** Re-login (max 2 tentativas)

## Seletores

> 🔴 **PREENCHER NA PRIMEIRA CONFIGURAÇÃO**

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
    coupon_activate_button: "TODO"
    poupa_balance: "TODO"
  checkout:
    delivery_slots: "TODO"
    payment_methods: "TODO"
    confirm_button: "TODO"
    order_number: "TODO"
  common:
    cookie_accept_minimal: "TODO"
    store_selector: "TODO"
    close_popup: "TODO"
```
