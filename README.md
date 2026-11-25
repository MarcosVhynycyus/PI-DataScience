# PI Data Science — Espaço MR | CHS

Projeto interdisciplinar de Data Science voltado à análise de dados do varejo do **Espaço MR**, com o objetivo de apoiar decisões e desenvolver recomendações de produtos.

O repositório reúne infraestrutura de laboratório, geração de dados sintéticos, uma API de consulta, rotinas de coleta e tratamento de dados e configuração de monitoramento. O sistema de recomendação com Big Data é o objetivo da solução; sua implementação ainda está em desenvolvimento.

## Estado atual

| Componente | Implementação presente no repositório |
| --- | --- |
| Infraestrutura | OpenTofu com QEMU/KVM, libvirt e cloud-init para duas VMs Ubuntu Server 24.04; geração do inventário Ansible. |
| Automação | Um playbook Ansible atualiza pacotes, implanta o simulador com Docker Compose e configura o monitoramento. |
| Simulador | Geração contínua de dados sintéticos com inconsistências intencionais para exercícios de qualidade de dados. |
| Serviços de dados | PostgreSQL 15, API Flask com Gunicorn e Adminer, definidos no Docker Compose do simulador. |
| Data Lake local | CSVs brutos e tratados publicados pelo R Markdown em `big-data/datalake/`. As rotinas em Python também podem gerar esses CSVs. |
| ETL em R | O R Markdown coleta a API, faz diagnóstico, limpeza e validação e publica os CSVs para os notebooks. |
| Data Warehouse | Arquivo SQLite e script para exportação das tabelas em CSV. |
| Monitoramento | Prometheus, Node Exporter e dashboard automático no Grafana, com métricas do gerador habilitadas por padrão. Alertas ainda não configurados. |

HDFS, processamento distribuído com Spark, integração automatizada entre todas as etapas e modelos de recomendação fazem parte da evolução proposta. Os documentos de arquitetura e pipeline também descrevem esse escopo planejado.

## Estrutura do repositório

```text
.
├── infra/
│   ├── iac/
│   │   ├── main.tf              # VMs, discos, cloud-init e inventário
│   │   ├── variables.tf         # Chave SSH e MACs opcionais
│   │   ├── cloud_init.cfg       # Configuração inicial das VMs
│   │   └── inventory.tpl        # Modelo do inventário Ansible
│   ├── ansible/playbooks/setup.yml
│   └── README.md
├── simulator/
│   ├── docker-compose.yml      # PostgreSQL, API, gerador e Adminer
│   ├── Dockerfile
│   ├── app.py                  # API Flask
│   ├── database.py             # Conexão com PostgreSQL
│   ├── stream_generator.py     # Geração contínua
│   ├── gerador.py              # Geração e inserção de inconsistências
│   ├── parametros.py
│   ├── quebras.py
│   └── requirements.txt
├── big-data/
│   ├── datalake/
│   │   ├── importer.py         # API → CSVs em raw_data/
│   │   └── limpeza.py          # raw_data/ → clean_data/
│   ├── datawarehouse/
│   │   ├── datawarehouse.db    # Banco SQLite
│   │   └── exporter.py         # Exportação de tabelas para CSV
│   └── vendas_db_stream/       # Arquivos de entrada e checkpoints
├── pipeline/
│   ├── etl.r                   # Tratamento de dados em R
│   ├── etl.Rmd                 # Documento R Markdown
│   ├── data/                   # CSVs de entrada do ETL em R
│   ├── raw_data/               # CSVs brutos gerados pelo R Markdown
│   ├── clean_data/             # CSVs tratados
│   └── README.md
├── monitoring/README.md
├── docs/arquitetura.md
└── README.md
```

## Infraestrutura do laboratório

O OpenTofu define duas VMs, cada uma com **1 vCPU, 1 GB de RAM e disco de 10 GB**:

| VM | Grupo Ansible | Finalidade |
| --- | --- | --- |
| `devops-1` | `monitoring` | Grafana e evolução do monitoramento. |
| `devops-2` | `simulator` | Execução dos serviços do simulador. |

Para provisionar o laboratório, o host precisa de Linux com virtualização KVM, QEMU/libvirt com rede e pool chamados `default`, OpenTofu, Ansible e acesso SSH. A imagem Ubuntu é baixada durante o provisionamento. O cloud-init configura o usuário `marcos` nas VMs.

### Clonar e provisionar

```bash
git clone https://github.com/MarcosVhynycyus/PI-DataScience.git
cd PI-DataScience
```

Caso ainda não tenha uma chave para o laboratório, crie-a no caminho padrão:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/devops_lab
```

Para usar outra chave, configure a variável `ssh_key_path` do OpenTofu. O arquivo público correspondente, com extensão `.pub`, também precisa existir.

```bash
cd infra/iac
tofu init
tofu validate
tofu plan
tofu apply
tofu output ips
cd ../..
```

O provisionamento gera `infra/ansible/inventory.ini`. A partir da raiz do repositório, execute:

```bash
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbooks/setup.yml
```

O playbook aguarda SSH e cloud-init, atualiza os pacotes e instala Docker, Compose e Buildx nas duas VMs. Ele copia `simulator/` para a VM geradora, inicia PostgreSQL, API, gerador e Adminer, e provisiona Node Exporter, Prometheus e Grafana. A execução verifica as tabelas, a API, a coleta das métricas e o dashboard. Ao final, a saída do playbook inclui `SIMULATOR_API_URL` para o R Markdown.

Os arquivos de estado do OpenTofu, `terraform.tfvars`, `.terraform/` e o inventário gerado são específicos de cada ambiente e não devem ser versionados. Consulte os detalhes em [Infraestrutura](infra/README.md).

## Executar o simulador

Para executar o simulador fora das VMs do laboratório, use estes comandos em uma máquina com Docker e o plugin Docker Compose:

```bash
docker compose -f simulator/docker-compose.yml up -d --build
docker compose -f simulator/docker-compose.yml logs -f generator
```

O gerador inicializa os dados e produz vendas continuamente. O Compose configura `--taxa-erro 0.04` para inserir inconsistências nos dados sintéticos de clientes, vendedores, estoque, vendas, crediário e promoções.

| Serviço | Acesso padrão |
| --- | --- |
| API Flask | `http://<IP_DO_SIMULADOR>:5000` |
| PostgreSQL | `<IP_DO_SIMULADOR>:5432` |
| Adminer | `http://<IP_DO_SIMULADOR>:8080` |

No Adminer, selecione PostgreSQL e use o servidor `db`, banco `varejo_db`, usuário `user` e senha `password`, conforme o Compose. Essas credenciais são destinadas ao laboratório.

Após a inicialização do banco e das tabelas, consulte a API:

```bash
curl http://localhost:5000/health
curl 'http://localhost:5000/api/vendas?limit=10&offset=0'
curl http://localhost:5000/api/tabelas/clientes
```

Substitua `localhost` pelo IP do simulador ao acessar de outra máquina. A API também disponibiliza `/api/tabelas/all` e `/api/tabelas/<nome_tabela>` para as seis tabelas geradas.

Para encerrar os serviços, preservando o volume do banco:

```bash
docker compose -f simulator/docker-compose.yml down
```

## Coletar e tratar os dados

### Rotinas em Python

Use Python 3.10 ou superior em um ambiente virtual. A limpeza utiliza pandas 2 ou superior para interpretar datas em formatos mistos.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'pandas>=2' numpy requests
```

Antes da coleta, ajuste as URLs em `big-data/datalake/importer.py` para o IP da sua API. O script contém um endereço fixo do laboratório e exige que as tabelas já estejam disponíveis.

Execute os comandos a partir da raiz do repositório, pois os scripts usam caminhos relativos:

```bash
python big-data/datalake/importer.py
python big-data/datalake/limpeza.py
```

A coleta salva CSVs em `big-data/datalake/raw_data/`. A limpeza padroniza textos, datas e campos numéricos, entre outros tratamentos, e grava os resultados em `big-data/datalake/clean_data/`.

### Rotinas em R

Para coletar, limpar e publicar os dados pelo R Markdown, substitua `<IP_SIMULATOR>` pelo endereço da VM geradora:

```bash
SIMULATOR_API_URL='http://<IP_SIMULATOR>:5000/api/tabelas' \
  Rscript -e 'rmarkdown::render("pipeline/etl.Rmd")'
```

O relatório gera `pipeline/raw_data/<tabela>.csv` e `pipeline/clean_data/<tabela>_clean.csv`. Depois da validação, atualiza os arquivos `<tabela>.csv` em `big-data/datalake/raw_data/` e `big-data/datalake/clean_data/`. Veja as dependências e o modo offline na [documentação do pipeline](pipeline/README.md).

O script `etl.r` também pode ser executado com os seis CSVs de `pipeline/data/`:

```bash
cd pipeline
Rscript etl.r
cd ..
```

O script `etl.r` carrega suas dependências via `pacman` e grava os resultados em `pipeline/clean_data/`.

### Exportar o SQLite

Para exportar as tabelas do banco existente, execute a partir da raiz:

```bash
python3 big-data/datawarehouse/exporter.py
```

Atualmente, o script lê `big-data/datawarehouse/datawarehouse.db` e grava os CSVs em `DA/datawarehouse/csv/`. As rotinas de limpeza e exportação são independentes; esses comandos não carregam automaticamente os dados tratados no SQLite.

## Acessar o Grafana

Após executar o playbook, acesse `http://<IP_DA_VM_MONITORING>:3000` com o usuário `admin`. A senha inicial é gerada e armazenada na VM; consulte-a com:

```bash
ansible monitoring -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command \
  -a 'cat /opt/monitoring/grafana_admin_password'
```

O Grafana utiliza um volume Docker persistente. O Ansible provisiona a fonte Prometheus e o dashboard **Monitoramento — VM Geradora**, na pasta **Infraestrutura**, com atualização a cada 15 segundos. O dashboard também está em `http://<IP_DA_VM_MONITORING>:3000/d/vm-geradora`; Prometheus fica em `http://<IP_DA_VM_MONITORING>:9090`.

Para reaplicar o monitoramento de um ambiente em funcionamento, use:

```bash
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbooks/monitoring.yml
```

Consulte a arquitetura, as portas e os comandos de validação em [Monitoramento e observabilidade](monitoring/README.md).

## Documentação complementar

- [Infraestrutura e provisionamento](infra/README.md)
- [Arquitetura proposta e fluxo de dados](docs/arquitetura.md)
- [Pipeline ETL em R Markdown](pipeline/README.md)
- [Monitoramento e observabilidade](monitoring/README.md)

Projeto Interdisciplinar em Data Science — **Espaço MR | CHS**.
