# PI Data Science — Espaço MR | CHS

Projeto interdisciplinar de Data Science voltado à análise de dados do varejo do **Espaço MR**, com o objetivo de apoiar decisões e desenvolver recomendações de produtos.

O repositório reúne infraestrutura de laboratório, geração de dados sintéticos, uma API de consulta, rotinas de coleta e tratamento de dados e configuração de monitoramento. O sistema de recomendação com Big Data é o objetivo da solução; sua implementação ainda está em desenvolvimento.

## Estado atual

| Componente | Implementação presente no repositório |
| --- | --- |
| Infraestrutura | OpenTofu com QEMU/KVM, libvirt e cloud-init para duas VMs Ubuntu Server 24.04; geração do inventário Ansible. |
| Automação | Playbook Ansible para instalar Docker, configurar o Grafana e preparar dependências e diretório do simulador. |
| Simulador | Geração contínua de dados sintéticos com inconsistências intencionais para exercícios de qualidade de dados. |
| Serviços de dados | PostgreSQL 15, API Flask com Gunicorn e Adminer, definidos no Docker Compose do simulador. |
| Data Lake local | Coleta da API para CSV e limpeza com Python, pandas e NumPy. |
| ETL em R | Script e documento R Markdown para diagnóstico, limpeza e transformação de CSVs. |
| Data Warehouse | Arquivo SQLite e script para exportação das tabelas em CSV. |
| Monitoramento | Provisionamento do Grafana via Ansible; fontes de dados, dashboards, Prometheus e alertas ainda precisam ser configurados. |

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

O provisionamento gera `infra/ansible/inventory.ini`. Depois que o cloud-init terminar e o SSH estiver disponível, teste a conexão e execute o playbook:

```bash
ansible all -i infra/ansible/inventory.ini -m ping
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbooks/setup.yml
```

O playbook configura o Grafana na VM de monitoramento. Na VM do simulador, instala dependências e cria `/opt/simulator`; a cópia do código e a inicialização dos serviços do simulador são etapas manuais.

Os arquivos de estado do OpenTofu, `terraform.tfvars`, `.terraform/` e o inventário gerado são específicos de cada ambiente e não devem ser versionados. Consulte os detalhes em [Infraestrutura](infra/README.md).

## Executar o simulador

Na máquina que hospedará o simulador, com Docker e o plugin Docker Compose instalados, execute a partir da raiz de uma cópia do repositório:

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

Com R instalado e os seis CSVs disponíveis em `pipeline/data/`, execute:

```bash
cd pipeline
Rscript etl.r
cd ..
```

O script carrega os pacotes `tidyverse`, `lubridate`, `scales`, `knitr` e `janitor` via `pacman`, podendo instalá-los na primeira execução. Os resultados são gravados em `pipeline/clean_data/`. O arquivo `pipeline/etl.Rmd` contém a versão em R Markdown.

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

O Grafana utiliza um volume Docker persistente. O playbook verifica sua disponibilidade em `/api/health`; a coleta de métricas e os dashboards dependem de configuração adicional. Consulte [Monitoramento e observabilidade](monitoring/README.md) para opções de imagem, porta e detalhes de acesso.

## Documentação complementar

- [Infraestrutura e provisionamento](infra/README.md)
- [Arquitetura proposta e fluxo de dados](docs/arquitetura.md)
- [Escopo planejado dos pipelines ETL](pipeline/README.md)
- [Monitoramento e observabilidade](monitoring/README.md)

Projeto Interdisciplinar em Data Science — **Espaço MR | CHS**.
