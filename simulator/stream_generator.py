import random
import time
import pandas as pd
from sqlalchemy import text
from database import engine

# Importações diretas dos módulos locais
from gerador import (
    gerar_clientes, gerar_vendedores, gerar_estoque, 
    gerar_vendas, gerar_crediario, gerar_promocoes,
    sujar_clientes, sujar_estoque, sujar_vendas, 
    sujar_crediario, sujar_promocoes
)
from parametros import parse_args

def inicializar_dimensoes(args):
    """Gera as tabelas de dimensão iniciais caso ainda não existam no banco."""
    with engine.connect() as conn:
        tabelas_existentes = engine.dialect.get_table_names(conn)

    if "clientes" not in tabelas_existentes:
        print("Inicializando dimensão Clientes...")
        clientes = gerar_clientes(args.clientes)
        clientes = sujar_clientes(clientes, args.taxa_erro)
        clientes.to_sql("clientes", engine, if_exists="replace", index=False)

    if "vendedores" not in tabelas_existentes:
        print("Inicializando dimensão Vendedores...")
        vendedores = gerar_vendedores(args.vendedores)
        vendedores.to_sql("vendedores", engine, if_exists="replace", index=False)

    if "estoque" not in tabelas_existentes:
        print("Inicializando dimensão Estoque...")
        estoque = gerar_estoque(args.produtos)
        estoque = sujar_estoque(estoque, args.taxa_erro)
        estoque.to_sql("estoque", engine, if_exists="replace", index=False)

def rodar_simulador():
    args = parse_args()
    inicializar_dimensoes(args)

    print("Iniciando fluxo contínuo de geração de vendas e eventos...")
    
    clientes_df = pd.read_sql("SELECT id_cliente FROM clientes", engine)
    vendedores_df = pd.read_sql("SELECT * FROM vendedores", engine)
    estoque_df = pd.read_sql("SELECT * FROM estoque", engine)
    
    ids_cliente_validos = clientes_df["id_cliente"].dropna().tolist()

    while True:
        try:
            with engine.connect() as conn:
                # 1. Busca o maior ID diretamente no banco; se a tabela não existir, assume 0
                try:
                    ultimo_id_venda = conn.execute(text("SELECT COALESCE(MAX(id_venda), 0) FROM vendas")).scalar() or 0
                except Exception:
                    ultimo_id_venda = 0

                try:
                    ultimo_id_parcela = conn.execute(text("SELECT COALESCE(MAX(id_parcela), 0) FROM crediario")).scalar() or 0
                except Exception:
                    ultimo_id_parcela = 0

                try:
                    ultimo_id_promocao = conn.execute(text("SELECT COALESCE(MAX(id_promocao), 0) FROM promocoes")).scalar() or 0
                except Exception:
                    ultimo_id_promocao = 0

            # 2. Gera o lote passando o id_inicio correto
            qtd_vendas_lote = random.randint(5, 20)
            vendas = gerar_vendas(
                qtd_vendas_lote, clientes_df, vendedores_df, estoque_df, 
                id_inicio=ultimo_id_venda + 1
            )
            crediario = gerar_crediario(
                vendas, 
                id_inicio_parcela=ultimo_id_parcela + 1
            )
            promocoes = gerar_promocoes(
                1, estoque_df, 
                id_inicio_promocao=ultimo_id_promocao + 1
            )

            # 3. Injeta ruídos/falhas
            vendas = sujar_vendas(vendas, args.taxa_erro, ids_cliente_validos)
            crediario = sujar_crediario(crediario, args.taxa_erro)
            promocoes = sujar_promocoes(promocoes, args.taxa_erro)

            # 4. Insere no SQL (append)
            vendas.to_sql("vendas", engine, if_exists="append", index=False)
            if not crediario.empty:
                crediario.to_sql("crediario", engine, if_exists="append", index=False)
            promocoes.to_sql("promocoes", engine, if_exists="append", index=False)

            print(f"[{time.strftime('%H:%M:%S')}] +{len(vendas)} vendas inseridas no banco SQL.", flush=True)
            
            time.sleep(5)

        except Exception as e:
            print(f"Erro no ciclo do gerador: {e}")
            time.sleep(5)

if __name__ == "__main__":
    rodar_simulador()