# Módulo de Infraestrutura Big Data

Este repositório/módulo é responsável pela especificação, organização e armazenamento do **Data Lake** e do motor de processamento distribuído da arquitetura do Espaço MR.

---

## 🏗️ Componentes da Camada de Big Data

1. **Data Lake (HDFS - Hadoop Distributed File System):**
   - Atua como o repositório centralizado para dados brutos e semi-processados.
   - Organizado em três zonas principais:
     - `raw/`: Dados brutos provenientes do simulador e APIs.
     - `processing/`: Dados higienizados e padronizados.
     - `refined/`: Dados modelados prontos para análise e treinamento de Machine Learning.

2. **Motor de Processamento (Apache Spark):**
   - Utilizado para transformações de alto desempenho em memória.
   - Suporte nativo a execuções em modo **Batch** (para relatórios e matrizes pesadas) e **Streaming** (Spark Structured Streaming para logs de cliques).

3. **Data Warehouse:**
   - Camada analítica otimizada para consultas OLAP e construção de dashboards de tomada de decisão.

---

## 📁 Estrutura de Diretórios Internos do Data Lake (HDFS)

```text
hdfs://cluster-master:9000/espaco-mr/
├── raw/
│   ├── vendas/
│   ├── ecommerce/
│   └── redes_sociais/
├── processing/
│   ├── clientes_limpos/
│   └── interacoes_padronizadas/
└── refined/
    ├── dw_vendas/
    └── matriz_recomendacao/
```

---

## 🔧 Configurações do Cluster Spark

- **Modo de Implantação:** Standalone / YARN
- **Executores:** Configurados via Ansible no arquivo `inventory.ini`
- **Linguagem:** Python (PySpark 3.x)

Para checar o status do cluster Spark e do HDFS:
```bash
# Verificar HDFS
hdfs dfsadmin -report

# Verificar Spark Workers
spark-class org.apache.spark.deploy.master.Master
```