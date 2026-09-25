import argparse


def parse_args():
    p = argparse.ArgumentParser(description="Gerador de massa de dados simulados de um ERP de varejo")
    p.add_argument("--clientes", type=int, default=600)
    p.add_argument("--vendedores", type=int, default=25)
    p.add_argument("--produtos", type=int, default=180)
    p.add_argument("--vendas", type=int, default=9000)
    p.add_argument("--promocoes", type=int, default=15)
    p.add_argument("--taxa-erro", type=float, default=0.04,
                    help="fração de linhas afetadas por cada tipo de falha injetada (0 a 1)")
    p.add_argument("--seed", type=int, default=None, help="semente para reprodutibilidade")
    p.add_argument("--output", type=str, default="./data", help="diretório de saída dos CSVs")
    return p.parse_args()