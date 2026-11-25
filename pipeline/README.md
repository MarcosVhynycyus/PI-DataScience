# Pipeline ETL em R Markdown

O relatório `etl.Rmd` coleta as seis tabelas da API do simulador, diagnostica
a qualidade dos dados, aplica a limpeza e valida os CSVs tratados. Requer R,
Pandoc e os pacotes abaixo.

```r
install.packages(c("rmarkdown", "knitr", "tidyverse", "lubridate", "janitor", "httr2", "jsonlite"))
```

O relatório usa o `ansible_host` do grupo `[simulator]` em
`infra/ansible/inventory.ini`. Se o inventário estiver ausente, usa
`http://127.0.0.1:5000/api/tabelas`. Ao rodar as células no RStudio, o
relatório localiza o inventário a partir do `etl.Rmd` aberto no editor.
Em outras sessões interativas, use a raiz do repositório ou a pasta
`pipeline/` como diretório de trabalho do R.

Para informar outro endereço ao rodar as células, defina a variável no console
do R antes da execução.

```r
Sys.setenv(SIMULATOR_API_URL = "http://<IP_SIMULATOR>:5000/api/tabelas")
```

Para renderizar com o endereço do inventário, execute da raiz do repositório.

```bash
Rscript -e 'rmarkdown::render("pipeline/etl.Rmd")'
```

Para renderizar com outro endereço, use `SIMULATOR_API_URL`. Por exemplo, se o
simulador estiver rodando na própria máquina, use `127.0.0.1` no comando abaixo.

```bash
SIMULATOR_API_URL='http://<IP_SIMULATOR>:5000/api/tabelas' \
  Rscript -e 'rmarkdown::render("pipeline/etl.Rmd")'
```

| Dados | Arquivo local | Arquivo usado pelos notebooks |
| --- | --- | --- |
| Brutos | `pipeline/raw_data/<tabela>.csv` | `big-data/datalake/raw_data/<tabela>.csv` |
| Tratados | `pipeline/clean_data/<tabela>_clean.csv` | `big-data/datalake/clean_data/<tabela>.csv` |

A publicação usa os diretórios existentes do datalake e substitui os CSVs
correspondentes após a validação. Os arquivos também ficam em `pipeline/`.
Na renderização, um `url_api` preenchido tem precedência sobre
`SIMULATOR_API_URL` e o inventário.

## Reprocessar uma coleta

Com os seis CSVs brutos de uma extração anterior em `pipeline/raw_data/`,
execute em modo offline. O relatório publica os dados brutos dessa coleta e
os dados tratados da execução atual.

```bash
Rscript -e 'rmarkdown::render("pipeline/etl.Rmd", params = list(atualizar_api = FALSE))'
```

O script `etl.r` usa os arquivos em `pipeline/data/` e grava o tratamento em
`pipeline/clean_data/`.
