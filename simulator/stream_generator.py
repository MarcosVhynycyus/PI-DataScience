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
from metrics import GeneratorMetrics

metrics = GeneratorMetrics()

def inicializar_dimensoes(args):
    """Gera as tabelas de dimensão iniciais caso ainda não existam no banco."""
    with engine.connect() as conn:
        tabelas_existentes = engine.dialect.get_table_names(conn)

    if "clientes" not in tabelas_existentes:
        print("Inicializando dimensão Clientes...")
        clientes = gerar_clientes(args.clientes)
        clientes = sujar_clientes(clientes, args.taxa_erro)
        clientes.to_sql("clientes", engine, if_exists="replace", index=False)
        metrics.record_written("clientes", len(clientes))

    if "vendedores" not in tabelas_existentes:
        print("Inicializando dimensão Vendedores...")
        vendedores = gerar_vendedores(args.vendedores)
        vendedores.to_sql("vendedores", engine, if_exists="replace", index=False)
        metrics.record_written("vendedores", len(vendedores))

    if "estoque" not in tabelas_existentes:
        print("Inicializando dimensão Estoque...")
        estoque = gerar_estoque(args.produtos)
        estoque = sujar_estoque(estoque, args.taxa_erro)
        estoque.to_sql("estoque", engine, if_exists="replace", index=False)
        metrics.record_written("estoque", len(estoque))

def rodar_simulador():
    args = parse_args()
    metrics.start_server()
    try:
        inicializar_dimensoes(args)
    except Exception:
        metrics.failed("initialization")
        raise

    print("Iniciando fluxo contínuo de geração de vendas e eventos...")
    
    clientes_df = pd.read_sql("SELECT id_cliente FROM clientes", engine)
    vendedores_df = pd.read_sql("SELECT * FROM vendedores", engine)
    estoque_df = pd.read_sql("SELECT * FROM estoque", engine)
    
    ids_cliente_validos = clientes_df["id_cliente"].dropna().tolist()
    metrics.ready.set(1)

    while True:
        cycle_started = time.monotonic()
        try:
            with engine.connect() as conn:
                tabelas_existentes = engine.dialect.get_table_names(conn)
                ultimos_ids = {
                    tabela: conn.execute(text(f"SELECT MAX({coluna}) FROM {tabela}")).scalar() or 0
                    if tabela in tabelas_existentes else 0
                    for tabela, coluna in (("vendas", "id_venda"), ("crediario", "id_parcela"),
                                           ("promocoes", "id_promocao"))
                }

            # 2. Gera o lote passando o id_inicio correto
            qtd_vendas_lote = random.randint(5, 20)
            vendas = gerar_vendas(
                qtd_vendas_lote, clientes_df, vendedores_df, estoque_df, 
                id_inicio=ultimos_ids["vendas"] + 1
            )
            crediario = gerar_crediario(
                vendas, 
                id_inicio_parcela=ultimos_ids["crediario"] + 1
            )
            promocoes = gerar_promocoes(
                1, estoque_df, 
                id_inicio_promocao=ultimos_ids["promocoes"] + 1
            )

            sales_value = metrics.sales_value_before_noise(vendas)

            # 3. Injeta ruídos/falhas
            vendas = sujar_vendas(vendas, args.taxa_erro, ids_cliente_validos)
            crediario = sujar_crediario(crediario, args.taxa_erro)
            promocoes = sujar_promocoes(promocoes, args.taxa_erro)

            # 4. Insere no SQL (append)
            vendas.to_sql("vendas", engine, if_exists="append", index=False)
            metrics.record_written("vendas", len(vendas))
            if not crediario.empty:
                crediario.to_sql("crediario", engine, if_exists="append", index=False)
                metrics.record_written("crediario", len(crediario))
            promocoes.to_sql("promocoes", engine, if_exists="append", index=False)
            metrics.record_written("promocoes", len(promocoes))
            metrics.cycle_succeeded(len(vendas), time.monotonic() - cycle_started, sales_value)

            print(f"[{time.strftime('%H:%M:%S')}] +{len(vendas)} vendas inseridas no banco SQL.", flush=True)
            
            time.sleep(5)

        except Exception as e:
            metrics.failed("cycle")
            print(f"Erro no ciclo do gerador: {e}")
            time.sleep(5)

if __name__ == "__main__":
    rodar_simulador()
