import os
import sqlite3
import csv
from pathlib import Path

def sqlite_to_csv(db_path: str, output_dir: str = "./csv") -> None:
    """
    Exporta todas as tabelas de um banco de dados SQLite para arquivos CSV.
    """
    # Garante a criação da pasta de destino
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Lista todas as tabelas do usuário (ignora tabelas internas do SQLite)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    
    if not tables:
        print("Nenhuma tabela encontrada no banco de dados.")
        conn.close()
        return

    for table_name in tables:
        csv_file_path = output_path / f"{table_name}.csv"
        
        # Consulta os dados da tabela
        cursor.execute(f'SELECT * FROM "{table_name}"')
        rows = cursor.fetchall()
        
        # Extrai os nomes das colunas
        headers = [description[0] for description in cursor.description]
        
        # Grava os dados no arquivo CSV (UTF-8)
        with open(csv_file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"✓ Tabela '{table_name}' exportada para '{csv_file_path}'")
        
    conn.close()
    print("\nExportação concluída com sucesso!")

if __name__ == "__main__":
    NOME_DO_BANCO = "./big-data/datawarehouse/datawarehouse.db"
    
    if os.path.exists(NOME_DO_BANCO):
        sqlite_to_csv(NOME_DO_BANCO, output_dir="./DA/datawarehouse/csv")
    else:
        print(f"Erro: O arquivo '{NOME_DO_BANCO}' não foi encontrado.")