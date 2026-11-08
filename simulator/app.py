from flask import Flask, jsonify, request
import pandas as pd
from sqlalchemy import text 
from database import engine

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para a VM de Monitoring checar status da aplicação."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))  # <--- Envolva com text()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/api/vendas", methods=["GET"])
def get_vendas():
    """Endpoint consumidor para a pipeline de ETL/BigData extrair os dados."""
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    
    query = f"SELECT * FROM vendas ORDER BY id_venda DESC LIMIT {limit} OFFSET {offset}"
    df = pd.read_sql(query, engine)
    
    return jsonify(df.to_dict(orient="records")), 200

@app.route("/api/tabelas/<nome_tabela>", methods=["GET"])
def get_tabela(nome_tabela):
    """Endpoint genérico para extração total/parcial de tabelas."""
    tabelas_validas = ["clientes", "vendedores", "estoque", "vendas", "crediario", "promocoes"]
    if nome_tabela not in tabelas_validas:
        return jsonify({"error": "Tabela inválida"}), 400

    df = pd.read_sql(f"SELECT * FROM {nome_tabela}", engine)
    return jsonify(df.to_dict(orient="records")), 200

@app.route("/api/tabelas/all", methods=["GET"])
def get_all():
    try:
        df_vendas = pd.read_sql("SELECT * FROM vendas", engine)
        df_clientes = pd.read_sql("SELECT * FROM clientes", engine)
        df_estoque = pd.read_sql("SELECT * FROM estoque", engine)
        df_promocoes = pd.read_sql("SELECT * FROM promocoes", engine)
        df_crediario = pd.read_sql("SELECT * FROM crediario", engine)
        df_vendedores = pd.read_sql("SELECT * FROM vendedores", engine)

        dados = {
            "vendas": df_vendas.to_dict(orient="records"),
            "clientes": df_clientes.to_dict(orient="records"),
            "crediario": df_crediario.to_dict(orient="records"),
            "estoque": df_estoque.to_dict(orient="records"),
            "promocoes": df_promocoes.to_dict(orient="records"),
            "vendedores": df_vendedores.to_dict(orient="records"),
        }

        return jsonify(dados), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)