import os 
import requests as rq
import pandas as pd

vendas_url = "http://192.168.122.92:5000/api/tabelas/vendas"
vendedores_url = "http://192.168.122.92:5000/api/tabelas/vendedores"
clientes_url = "http://192.168.122.92:5000/api/tabelas/clientes"
crediario_url = "http://192.168.122.92:5000/api/tabelas/crediario"
promocoes_url = "http://192.168.122.92:5000/api/tabelas/promocoes"
estoque_url = "http://192.168.122.92:5000/api/tabelas/estoque"

output_dir = "./big-data/datalake/raw_data"

vendas_file_path = os.path.join(output_dir, "vendas.csv")
vendedores_file_path = os.path.join(output_dir, "vendedores.csv")
clientes_file_path = os.path.join(output_dir, "clientes.csv")
crediario_file_path = os.path.join(output_dir, "crediario.csv")
promocoes_file_path = os.path.join(output_dir, "promocoes.csv")
estoque_file_path = os.path.join(output_dir, "estoque.csv")

os.makedirs(output_dir, exist_ok=True)

try:
    vendas_response = rq.get(vendas_url)
    vendas_response.raise_for_status()
    vendas_data = vendas_response.json()
    vendas_df = pd.DataFrame(vendas_data)
    vendas_df.to_csv(vendas_file_path, index=False, encoding="utf-8")
    print(f"Dados salvos com sucesso em {vendas_file_path}")

    vendedores_response = rq.get(vendedores_url)
    vendedores_response.raise_for_status()
    vendedores_data = vendedores_response.json()
    vendedores_df = pd.DataFrame(vendedores_data)
    vendedores_df.to_csv(vendedores_file_path, index=False, encoding="utf-8")
    print(f"Dados salvos com sucesso em {vendedores_file_path}")

    clientes_response = rq.get(clientes_url)
    clientes_response.raise_for_status()
    clientes_data = clientes_response.json()
    clientes_df = pd.DataFrame(clientes_data)
    clientes_df.to_csv(clientes_file_path, index=False, encoding="utf-8")
    print(f"Dados salvos com sucesso em {clientes_file_path}")

    crediario_response = rq.get(crediario_url)
    crediario_response.raise_for_status()
    crediario_data = crediario_response.json()
    crediario_df = pd.DataFrame(crediario_data)
    crediario_df.to_csv(crediario_file_path, index=False, encoding="utf-8")
    print(f"Dados salvos com sucesso em {crediario_file_path}")

    promocoes_response = rq.get(promocoes_url)
    promocoes_response.raise_for_status()
    promocoes_data = promocoes_response.json()
    promocoes_df = pd.DataFrame(promocoes_data)
    promocoes_df.to_csv(promocoes_file_path, index=False, encoding="utf-8")
    print(f"Dados salvos com sucesso em {promocoes_file_path}")

    estoque_response = rq.get(estoque_url)
    estoque_response.raise_for_status()
    estoque_data = estoque_response.json()
    estoque_df = pd.DataFrame(estoque_data)
    estoque_df.to_csv(estoque_file_path, index=False, encoding="utf-8")
    print(f"Dados salvos com sucesso em {estoque_file_path}")

except rq.exceptions.RequestException as e:
    print(f"Erro ao acessar API: {e}")
except Exception as e:
    print(f"Erro na execução do script: {e}")

