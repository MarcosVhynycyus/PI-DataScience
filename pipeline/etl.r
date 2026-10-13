# 1. CARREGAMENTO DE BIBLIOTECAS E DADOS ---------------------------------------
if (!require("pacman")) install.packages("pacman")
pacman::p_load(tidyverse, lubridate, scales, knitr)

# Leitura dos arquivos CSV
clientes   <- read.csv("../simulator/src/data/clientes.csv", stringsAsFactors = FALSE, encoding = "UTF-8")
crediario  <- read.csv("../simulator/src/data/crediario.csv", stringsAsFactors = FALSE, encoding = "UTF-8")
estoque    <- read.csv("../simulator/src/data/estoque.csv", stringsAsFactors = FALSE, encoding = "UTF-8")
promocoes  <- read.csv("../simulator/src/data/promocoes.csv", stringsAsFactors = FALSE, encoding = "UTF-8")
vendas     <- read.csv("../simulator/src/data/vendas.csv", stringsAsFactors = FALSE, encoding = "UTF-8")
vendedores <- read.csv("../simulator/src/data/vendedores.csv", stringsAsFactors = FALSE, encoding = "UTF-8")

# 2. TRATATIVA E HIGIENIZAÇÃO DOS DADOS ----------------------------------------

# Função auxiliar para limpeza de colunas monetárias
limpar_moeda <- function(x) {
  if (is.numeric(x)) return(x)
  x %>%
    str_replace_all("R\\$", "") %>%
    str_replace_all("\\s", "") %>%
    str_replace_all("\\.", "") %>%
    str_replace_all(",", ".") %>%
    as.numeric()
}

2.1 Tratativa do Dataset de Clientes
clientes_clean <- clientes %>%
  distinct(id_cliente, .keep_all = TRUE) %>%
  mutate(
    cidade = case_when(
      str_detect(cidade, "Tamba") ~ "Tambaú",
      str_detect(cidade, "SÃ£o JoÃ£o|São João") ~ "São João da Boa Vista",
      str_detect(cidade, "Agua") ~ "Aguaí",
      TRUE ~ cidade
    ),
    canal_preferencial = str_to_title(str_trim(canal_preferencial)),
    idade = ifelse(idade < 15 | idade > 100, NA, idade), # Remoção de outliers/erros
    data_cadastro = as.Date(data_cadastro)
  )

# 2.2 Tratativa do Dataset de Estoque
estoque_clean <- estoque %>%
  mutate(
    preco_unitario = limpar_moeda(preco_unitario),
    data_entrada   = as.Date(data_entrada),
    ultima_venda   = as.Date(ultima_venda),
    calc_estoque   = quantidade_entrada - quantidade_saida,
    divergencia_fisico_atual = estoque_atual != estoque_fisico,
    status_estoque = case_when(
      estoque_fisico < estoque_minimo ~ "Ruptura / Abaixo do Mínimo",
      estoque_fisico > estoque_maximo ~ "Excesso / Overstock",
      TRUE ~ "Ideal"
    )
  )

# 2.3 Tratativa do Dataset de Vendas
vendas_clean <- vendas %>%
  distinct(id_venda, .keep_all = TRUE) %>% # Remoção de vendas duplicadas
  filter(quantidade > 0) %>%              # Invalidação de quantidades nulas/negativas
  mutate(
    preco_unitario = limpar_moeda(preco_unitario),
    valor_total_original = limpar_moeda(valor_total),
    valor_total_calculado = (quantidade * preco_unitario) - desconto,
    data_venda = parse_date_time(data_venda, orders = c("Ymd", "dmY", "dmy")),
    data_venda = as.Date(data_venda),
    mes_ano    = floor_date(data_venda, "month"),
    forma_pagamento = str_to_title(str_trim(forma_pagamento)),
    forma_pagamento = case_when(
      str_detect(forma_pagamento, "Crédito|Credito") ~ "Cartão de Crédito",
      str_detect(forma_pagamento, "Débito|Debito")   ~ "Cartão de Débito",
      str_detect(forma_pagamento, "Pix|PIX")          ~ "PIX",
      str_detect(forma_pagamento, "Crediário")       ~ "Crediário",
      str_detect(forma_pagamento, "Dinheiro")        ~ "Dinheiro",
      TRUE ~ forma_pagamento
    )
  )

# 2.4 Tratativa do Dataset de Crediário
crediario_clean <- crediario %>%
  mutate(
    status = str_to_title(str_trim(status)),
    status = case_when(
      status %in% c("Pago", "pago", "PAGO") ~ "Pago",
      status %in% c("Em Aberto", "Em aberto", "EM ABERTO", "em aberto") ~ "Em Aberto",
      TRUE ~ status
    ),
    data_vencimento = as.Date(data_vencimento),
    data_pagamento  = as.Date(data_pagamento)
  )

# 3. CONSTRUÇÃO DE TABELAS RESUMO (ANÁLISE PRELIMINAR) ------------------------

# Tabela 1: Resumo Geral do Faturamento por Canal
tb_canal <- vendas_clean %>%
  group_by(canal) %>%
  summarise(
    Transacoes = n(),
    Pecas_Vendidas = sum(quantidade),
    Faturamento_R = sum(valor_total_calculado),
    Ticket_Medio_R = mean(valor_total_calculado)
  )

print("--- VISÃO POR CANAL DE VENDA ---")
print(knitr::kable(tb_canal, digits = 2))

# Tabela 2: Resumo de Desempenho por Categoria de Produto
tb_categoria <- vendas_clean %>%
  group_by(categoria) %>%
  summarise(
    Transacoes = n(),
    Quantidade = sum(quantidade),
    Faturamento_R = sum(valor_total_calculado),
    Desconto_Total_R = sum(desconto),
    Preco_Medio_R = mean(preco_unitario)
  ) %>%
  arrange(desc(Faturamento_R))

print("--- PERFORMANCE POR CATEGORIA ---")
print(knitr::kable(tb_categoria, digits = 2))

# Tabela 3: Inadimplência e Situação do Crediário
tb_crediario <- crediario_clean %>%
  group_by(status) %>%
  summarise(
    Qtd_Parcelas = n(),
    Valor_Total_R = sum(valor_parcela),
    Valor_Em_Aberto_R = sum(valor_em_aberto),
    Dias_Atraso_Medio = mean(dias_atraso)
  )

print("--- SITUAÇÃO DO CREDIÁRIO ---")
print(knitr::kable(tb_crediario, digits = 2))

# Tabela 4: Nível de Risco e Ruptura no Estoque
tb_estoque_status <- estoque_clean %>%
  count(status_estoque, name = "Qtd_Produtos") %>%
  mutate(Percentual = Qtd_Produtos / sum(Qtd_Produtos) * 100)

print("--- DIAGNÓSTICO DE ESTOQUE ---")
print(knitr::kable(tb_estoque_status, digits = 2))


# 4. GERAÇÃO DE GRÁFICOS ANALÍTICOS (GGPLOT2) ----------------------------------

# Gráfico 1: Evolução Mensal do Faturamento
g1 <- ggplot(vendas_clean %>% group_by(mes_ano) %>% summarise(Faturamento = sum(valor_total_calculado)), 
             aes(x = mes_ano, y = Faturamento)) +
  geom_line(color = "#2c3e50", size = 1.2) +
  geom_point(color = "#e74c3c", size = 3) +
  scale_y_continuous(labels = dollar_format(prefix = "R$ ", big.mark = ".", decimal.mark = ",")) +
  scale_x_date(date_labels = "%b/%Y", date_breaks = "1 month") +
  theme_minimal() +
  labs(title = "Evolução do Faturamento Mensal (2026)", x = "Mês", y = "Faturamento Total")

print(g1)

# Gráfico 2: Faturamento Total por Categoria de Produto
g2 <- ggplot(tb_categoria, aes(x = reorder(categoria, Faturamento_R), y = Faturamento_R, fill = categoria)) +
  geom_col(show.legend = FALSE) +
  coord_flip() +
  scale_y_continuous(labels = dollar_format(prefix = "R$ ", big.mark = ".", decimal.mark = ",")) +
  theme_minimal() +
  labs(title = "Faturamento Bruto por Categoria de Produto", x = "Categoria", y = "Faturamento (R$)")

print(g2)

# Gráfico 3: Distribuição das Formas de Pagamento
g3 <- vendas_clean %>%
  count(forma_pagamento) %>%
  ggplot(aes(x = reorder(forma_pagamento, n), y = n, fill = forma_pagamento)) +
  geom_col(show.legend = FALSE) +
  geom_text(aes(label = n), hjust = -0.2) +
  coord_flip() +
  theme_minimal() +
  labs(title = "Volume de Vendas por Forma de Pagamento", x = "Forma de Pagamento", y = "Número de Transações")

print(g3)

# Gráfico 4: Avaliação da Eficácia das Promoções (Vendas Antes vs Durante)
g4 <- promocoes %>%
  pivot_longer(cols = c(vendas_antes, vendas_durante), names_to = "Periodo", values_to = "Volume") %>%
  mutate(Periodo = ifelse(Periodo == "vendas_antes", "Antes da Promoção", "Durante a Promoção")) %>%
  ggplot(aes(x = reorder(produto, Volume), y = Volume, fill = Periodo)) +
  geom_bar(stat = "identity", position = "dodge") +
  coord_flip() +
  theme_minimal() +
  scale_fill_manual(values = c("#95a5a6", "#2ecc71")) +
  labs(title = "Efeito Promocional no Volume de Vendas por Produto", x = "Produto", y = "Unidades Vendidas", fill = "Período")

print(g4)
