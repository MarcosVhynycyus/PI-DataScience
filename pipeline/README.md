# Módulo de Pipelines de Dados (ETL)

Este diretório contém os scripts do pipeline de **Extração, Transformação e Carga (ETL)**, responsáveis por converter os dados brutos armazenados no Data Lake em dados consolidados no Data Warehouse.

---

## 🔄 Estágios do Pipeline de ETL

O pipeline de tratamento é executado pelo Apache Spark e segue três etapas principais:

```text
+-------------------+     +-------------------------+     +-------------------+
|  Dados Brutos     | --> |     Tratamento / ETL    | --> | Apache Spark / DW |
| (Data Lake / HDFS)|     | - Remoção Duplicidades  |     | (Dados Tratados)  |
|                   |     | - Padronização          |     |                   |
|                   |     | - Tratamento Ausentes   |     |                   |
+-------------------+     +-------------------------+     +-------------------+
```

### 1. Remoção de Duplicidades
- Identificação de transações ou cliques repetidos por meio de IDs únicos e janelas de tempo (`dropDuplicates()`).

### 2. Padronização dos Dados
- Unificação de formatos de data (`YYYY-MM-DD HH:mm:ss`).
- Normalização de strings e categorias de produtos.
- Conversão de moedas e unidades de medida.

### 3. Tratamento de Dados Ausentes
- Imputação de valores nulos em campos secundários.
- Descarte estruturado de registros corrompidos com registro de log de auditoria.

---

## ⚡ Modos de Execução

### Pipeline Batch (`etl_batch.py`)
Processa o histórico completo de transações e avaliações de clientes para gerar matrizes de filtragem colaborativa.

```bash
spark-submit --master local[*] etl_batch.py
```

### Pipeline Streaming (`etl_streaming.py`)
Captura dados de navegação e itens adicionados ao carrinho em tempo real para atualizar as recomendações da sessão do usuário.

```bash
spark-submit --master local[*] etl_streaming.py
```