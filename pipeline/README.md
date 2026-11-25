# Pipeline ETL em R Markdown

O relatório `etl.Rmd` coleta as seis tabelas da API do simulador, diagnostica
a qualidade dos dados, aplica a limpeza e valida os CSVs tratados. Requer R,
Pandoc e os pacotes abaixo.

```r
install.packages(c("rmarkdown", "knitr", "tidyverse", "lubridate", "janitor", "httr2", "jsonlite"))
```

Execute da raiz do repositório com o IP da VM geradora exibido pelo Ansible.
Para um simulador executado na própria máquina, o endereço padrão é
`http://127.0.0.1:5000/api/tabelas`.

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
O endereço da API pode ser passado pelo parâmetro `url_api` na renderização.

## Reprocessar uma coleta

Com os seis CSVs brutos de uma extração anterior em `pipeline/raw_data/`,
execute em modo offline. O relatório publica os dados brutos dessa coleta e
os dados tratados da execução atual.

```bash
Rscript -e 'rmarkdown::render("pipeline/etl.Rmd", params = list(atualizar_api = FALSE))'
```

O script `etl.r` usa os arquivos em `pipeline/data/` e grava o tratamento em
`pipeline/clean_data/`.
