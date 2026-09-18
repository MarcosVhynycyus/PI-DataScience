# Arquitetura do Sistema de Recomendação com Big Data

Este documento apresenta a arquitetura técnica e conceitual do **Sistema de Recomendação de Produtos do Espaço MR**, descrevendo o fluxo de ponta a ponta, desde a coleta até a tomada de decisão.

---

## 🎯 1. Definição do Problema e Solução

### Problema Identificado
Recomendar produtos relevantes e personalizados para cada cliente com base em seu histórico de compras e comportamento de navegação, aumentando a taxa de conversão, o ticket médio e melhorando a experiência geral do usuário.

### Solução Proposta
Uma plataforma híbrida de **Big Data + Machine Learning**, combinando técnicas de **Filtragem Colaborativa** e **Análise de Similaridade** entre produtos e perfis de clientes para gerar sugestões em tempo real e em lote.

---

## 🔀 2. Fluxo Geral da Arquitetura de Dados

O diagrama abaixo descreve as etapas de processamento e a movimentação dos dados na plataforma:

```text
+-------------------+      +-------------------+      +-------------------+
| Sistema de Vendas |      |    E-commerce     |      |   Redes Sociais   |
+---------+---------+      +---------+---------+      +---------+---------+
          |                          |                          |
          +-------------------+------+--------------------------+
                              |
                              v
                    +-------------------+
                    |  COLETA DOS DADOS |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | DATA LAKE / HDFS  |
                    +---------+---------+
                              |
                              v
               +-----------------------------+
               |       TRATAMENTO / ETL      |
               | - Remoção de duplicidades   |
               | - Padronização dos dados    |
               | - Tratamento dados ausentes |
               +--------------+--------------+
                              |
                              v
                    +-------------------+
                    |   APACHE SPARK    |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    |  DATA WAREHOUSE   |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    |   ANÁLISE / OLAP  |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    |    DASHBOARDS     |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | TOMADA DE DECISÃO |
                    +-------------------+
```

---

## 🗂️ 3. Origem e Tipos de Dados

O ecossistema consome dados de três formatos fundamentais:

| Categoria do Dado | Fonte de Origem | Exemplos de Conteúdo | Tipo de Dado |
| :--- | :--- | :--- | :--- |
| **Navegação & Interação** | E-commerce / Web App | Produtos visualizados, buscas, itens no carrinho, cliques em promoções | **Semiestruturado** (JSON/Logs) |
| **Transacional & Perfil** | Sistema de Vendas / ERP | Histórico de compras, cadastro de clientes, pagamentos | **Estruturado** (SQL) |
| **Opinião & Feedback** | Redes Sociais / Avaliações | Avaliações de produtos (reviews), comentários, mensagens de suporte | **Não Estruturado** (Texto livre) |

---

## ⚡ 4. As Características do Big Data (5 Vs)

1. **Volume:** Processamento de alto número de transações, interações e cliques de clientes acumulados continuamente.
2. **Variedade:** Integração de dados estruturados (bancos relacionais), semiestruturados (logs web) e não estruturados (textos e avaliações).
3. **Velocidade:** Geração constante de novos dados exigindo respostas rápidas para recomendações dinâmicas.
4. **Veracidade:** Higienização de dados na etapa de ETL para eliminação de inconsistências, ruídos e duplicidades.
5. **Valor:** Conversão de dados operacionais brutos em recomendações personalizadas que geram aumento do ticket médio.

---

## 🔄 5. Modos de Processamento

### Processamento Batch (Em Lote)
- **Foco:** Análise de histórico acumulado e identificação de padrões de longo prazo.
- **Frequência:** Execução diária/noturna via Apache Spark.
- **Saída:** Perfis de clientes atualizados e matrizes globais de recomendação.

### Processamento Streaming (Em Tempo Real)
- **Foco:** Recomendações imediatas com base na sessão ativa do usuário.
- **Frequência:** Processamento contínuo (latência em milissegundos/segundos).
- **Saída:** Sugestões dinâmicas atualizadas durante a navegação.

---

## 🛡️ 6. Benefícios, Desafios e LGPD

### Benefícios Esperados
- Aumento direto das vendas e do ticket médio.
- Maior relevância na comunicação com o cliente.
- Experiência de compra personalizada.

### Riscos e Desafios
- **Privacidade e Segurança dos Dados:** Criptografia e controle rigoroso de acesso aos dados pessoais.
- **Conformidade com a LGPD:** Anonimização de dados sensíveis e gestão do consentimento do cliente.
- **Qualidade dos Dados:** Riscos de viés ou ruído que levem a recomendações incorretas.
- **Custos de Infraestrutura:** Escalabilidade adequada do clusters para suporte ao alto volume.