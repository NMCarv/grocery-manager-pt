# Pingo Doce Online — Guia de Automação (Browser Tool)

> Este guia descreve como o agente deve navegar e interagir com o Pingo Doce Online
> usando a browser tool do OpenClaw (snapshots + refs numerados).
> Não usa seletores CSS hardcoded — o agente identifica elementos via AI snapshot.
>
> Última verificação do fluxo: 2026-02-22
> Se um passo falhar, notificar o utilizador para verificação manual.

## URLs

| Página | URL |
|---|---|
| Homepage | `https://www.pingodoce.pt/` |
| Login | `https://www.pingodoce.pt/login/` |
| Pesquisa | `https://www.pingodoce.pt/pesquisa/?q={query}` |
| Carrinho | `https://www.pingodoce.pt/carrinho/` |
| Checkout | `https://www.pingodoce.pt/checkout/` |
| Saldo Poupa | `https://www.pingodoce.pt/area-cliente/poupa/` |
| Cupões digitais | `https://www.pingodoce.pt/area-cliente/cupoes/` |

---

## Particularidades do Pingo Doce

**Cartão Poupa:** Sistema de descontos e pontos do Pingo Doce. Preços "Poupa" só são visíveis quando logado. Verificar saldo antes de comprar — pode ser aplicado como desconto direto.

**Cupões digitais:** Alguns descontos requerem ativação prévia na área de cliente. Ativar antes de adicionar produtos ao carrinho.

**Zona de entrega:** O Pingo Doce pode pedir seleção de loja/zona para entrega. Configurar para a zona correta de uma vez; deve persistir em sessões futuras.

**Mínimo de encomenda:** Verificar se existe valor mínimo para entrega (pode variar por zona).

---

## 1. Login

```
browser open "https://www.pingodoce.pt/login/"
browser snapshot
```

Identificar no snapshot:
- Campo de email/utilizador
- Campo de password
- Botão de login ("Entrar", "Iniciar sessão")

```
browser act type [ref_campo_email] "$PINGODOCE_EMAIL"
browser act type [ref_campo_password] "$PINGODOCE_PASSWORD"
browser act click [ref_botao_login]
```

**Verificar sucesso:** Novo snapshot após click. Sucesso se visível:
- Nome do utilizador ou "Olá, [Nome]" no header
- Ícone de área de cliente ativo

**Sessão persistente:** Browser profile `grocery` mantém cookies. Verificar se já está logado antes de repetir login.

**Verificação extra:** Se aparecer pedido de confirmação adicional → PAUSA. Notificar utilizador e aguardar resolução manual.

---

## 2. Gerir Popups e Banners

**Banner de cookies:**
```
browser snapshot
```
Se visível → procurar opção "Rejeitar não essenciais" ou equivalente e clicar.

**Seleção de zona/loja para entrega:**
Se o Pingo Doce pedir para selecionar a loja ou zona de entrega:
- Identificar o campo de localização ou lista de lojas
- Inserir o código postal ou selecionar a zona correta
- Confirmar seleção

Esta configuração deve persistir. Se aparecer de novo em sessões futuras, repetir.

---

## 3. Verificar e Ativar Cupões

Fazer **antes** de adicionar produtos ao carrinho.

```
browser open "https://www.pingodoce.pt/area-cliente/cupoes/"
browser snapshot
```

Para cada cupão disponível, identificar:
- Descrição do desconto
- Condições (categorias, valor mínimo, validade)
- Estado (ativo / por ativar)

Ativar cupões relevantes para a compra:
```
browser act click [ref_botao_ativar_cupao]
```

Registar lista de cupões ativados e poupança esperada.

---

## 4. Verificar Saldo Poupa

```
browser open "https://www.pingodoce.pt/area-cliente/poupa/"
browser snapshot
```

Extrair saldo disponível (formato: "X,XX €" ou "X pontos = X,XX €").
Guardar valor para usar no cálculo de otimização.

---

## 5. Pesquisa de Produtos

```
browser open "https://www.pingodoce.pt/pesquisa/?q=[query_url_encoded]"
browser snapshot
```

Para cada produto relevante nos resultados, extrair:

- **Nome:** Título/nome completo do produto
- **Preço atual:** Preço com cartão Poupa (visível por estar logado) — formato "X,XX €"
- **Preço sem Poupa:** Se mostrado em separado (preço sem cartão)
- **Preço por unidade:** "€/kg", "€/L", "€/un"
- **Promoção:** Badges como "Poupa 30%", "Promoção", percentagem de desconto
- **Disponibilidade:** Botão "Adicionar" ativo vs. "Esgotado" / indisponível na zona

**Nota sobre preços Poupa:** O preço com desconto Poupa é o preço efetivo para o cálculo de comparação.

**Estratégia de seleção:**
1. Marca preferida da família
2. Marca aceitável
3. Marca própria Pingo Doce
4. Se nada disponível → notificar, sugerir comprar no Continente

---

## 6. Adicionar ao Carrinho

```
browser act click [ref_botao_adicionar]
```

Verificar confirmação visual após adição. Ajustar quantidade se necessário (via botão "+" no carrinho ou input de quantidade).

**Delay:** 2-3 segundos entre adições.

**Produto indisponível na zona:** Pode aparecer produto listado mas com aviso de não estar disponível para entrega na zona configurada. Neste caso → notificar família, skip para alternativa.

**CAPTCHA:** PAUSA imediata → notificar utilizador → aguardar resolução manual.

---

## 7. Revisão do Carrinho

```
browser open "https://www.pingodoce.pt/carrinho/"
browser snapshot
```

Verificar:
- Lista de produtos (bate certo com o plano?)
- Subtotal
- Saldo Poupa aplicado automaticamente (se configurado)
- Custo de entrega

Se total difere >10% da estimativa → PAUSA, notificar.

```
browser screenshot
```
Enviar ao admin para aprovação.

---

## 8. Checkout

**Só avançar após ✅ explícito do admin.**

Prosseguir para checkout:
- Confirmar morada de entrega (deve bater com `data/family_preferences.json`)
- Selecionar slot de entrega (preferir sábado/domingo 10h-13h)
- Verificar custo de entrega e se existe opção gratuita

**Pagamento:**
- Selecionar método pré-guardado
- Verificar se saldo Poupa está a ser aplicado (deve aparecer como desconto)
- ❌ NUNCA introduzir dados bancários novos

**Confirmação:**
```
browser screenshot
```
Enviar screenshot do resumo ao admin. Aguardar ✅.

Após ✅:
```
browser act click [ref_confirmar_encomenda]
browser snapshot
```
Extrair número de encomenda.

---

## 9. Pós-Compra

1. Extrair número de encomenda da página de confirmação
2. Notificar família: "✅ Encomenda Pingo Doce confirmada! Nº [X]. Entrega [slot]. Total: €[X] (saldo Poupa: -€[Y])"
3. Gravar em `{baseDir}/data/shopping_history.json`
4. Executar tracker de consumo

---

## Comportamento em Caso de Falha

| Situação | Ação |
|---|---|
| Seletor / elemento não encontrado | Tentar após novo snapshot; se persistir → notificar |
| Produto esgotado | Notificar, sugerir alternativa ou comprar no Continente |
| Produto não disponível na zona | Notificar, mover para Continente |
| Saldo Poupa não aplicado | Verificar configuração; aplicar manualmente se possível |
| Sessão expirada | Re-login (máx 2 tentativas) |
| CAPTCHA | PAUSA, escalar ao utilizador |
| Mínimo de encomenda não atingido | Notificar utilizador, sugerir adicionar itens ou comprar tudo no Continente |
| Timeout | Retry 1x, depois notificar |
