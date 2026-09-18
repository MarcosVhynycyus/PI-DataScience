# PI DataScience - Espaço MR | Sistema de Recomendação com Big Data

Este repositório contém a infraestrutura, os pipelines de dados, simuladores e a documentação do projeto de **Sistema de Recomendação de Produtos com Big Data** do **Espaço MR**.

O objetivo do projeto é estruturar um ambiente completo em ambiente **Linux**, automatizado via **Ansible**, capaz de ingerir, tratar, processar e analisar grandes volumes de dados para alimentar um modelo de Machine Learning focado em recomendações personalizadas.

---

## 📂 Estrutura do Repositório

```text
PI DataScience - Espaço MR | CHS
├── ansible/
│   ├── playbooks/
│   │   └── setup.yml        # Playbook de provisionamento do ambiente
│   └── inventory.ini        # Inventário de servidores/hosts
├── big-data/
│   └── README.md            # Documentação da infraestrutura Big Data (HDFS/Spark)
├── docs/
│   └── arquitetura.md       # Arquitetura detalhada do projeto e fluxo de dados
├── monitoring/
│   └── README.md            # Documentação dos serviços de monitoramento e métricas
├── pipeline/
│   └── README.md            # Documentação dos pipelines de ETL (Batch & Streaming)
├── simulator/
│   └── README.md            # Gerador e simulador de dados de entrada
└── README.md                # Guia principal do projeto
```

---

## 🚀 Tecnologias e Ferramentas

- **Sistema Operacional Base:** Linux (Ubuntu Server / Debian)
- **Automação & Infraestrutura:** Ansible
- **Coleta & Ingestão:** Python / Kafka / APIs
- **Armazenamento:** Data Lake (HDFS) / Data Warehouse (PostgreSQL/ClickHouse)
- **Processamento de Dados:** Apache Spark (PySpark) - Batch e Streaming
- **Análise & Visualização:** OLAP / Dashboards (Metabase / PowerBI / Grafana)
- **Monitoramento:** Prometheus & Grafana

---

## 🧰 Requisitos Prévia

- Linux Ubuntu 22.04 LTS ou superior.
- Python 3.10+ instalado.
- Ansible 2.14+ configurado.
- Acesso SSH sem senha (chave pública) para os nós do inventário.

---

## 🛠️ Passo a Passo para Reprodução do Ambiente

### 1. Clonar o Repositório
```bash
git clone https://github.com/seu-usuario/pi-datascience-espaco-mr.git
cd pi-datascience-espaco-mr
```

### 2. Configurar o Inventário do Ansible
Edite o arquivo `ansible/inventory.ini` com as informações de IP e usuário das suas máquinas Linux target.

### 3. Executar a Automação de Provisionamento
Execute o playbook do Ansible para instalar o Java, Apache Spark, HDFS e demais dependências:

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbooks/setup.yml
```

### 4. Executar o Simulador de Dados
Para gerar eventos simulados (vendas, navegação e interações):

```bash
cd simulator
python simulator.py
```

### 5. Iniciar o Pipeline de Dados
Para rodar os jobs de processamento Spark em lote (Batch) ou em tempo real (Streaming):

```bash
cd pipeline
spark-submit --master local[*] main_pipeline.py
```

---

## 📊 Documentação Completa

Para compreender a fundo os aspectos conceituais e técnicos do projeto, consulte os arquivos específicos:

- [Arquitetura e Fluxo de Dados](docs/arquitetura.md)
- [Camada Big Data & HDFS](big-data/README.md)
- [Pipelines ETL](pipeline/README.md)
- [Simulador de Fontes](simulator/README.md)
- [Monitoramento & Observabilidade](monitoring/README.md)

---

## 👥 Autores & Contribuintes
Projeto Interdisciplinar em Data Science — **Espaço MR | CHS**.