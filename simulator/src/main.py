import os
import random
import pandas as pd

from faker import Faker
from gerador import gerar_clientes, gerar_crediario, gerar_estoque, gerar_promocoes, gerar_vendas, gerar_vendedores, sujar_clientes, sujar_crediario, sujar_estoque, sujar_promocoes, sujar_vendas
from parametros import parse_args
from carregamento import enviar_diretorio_sftp

fake = Faker("pt_BR")

def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)
        Faker.seed(args.seed)

    os.makedirs(args.output, exist_ok=True)

    print("Gerando tabelas base (estrutura relacional íntegra)...")
    clientes = gerar_clientes(args.clientes)
    vendedores = gerar_vendedores(args.vendedores)
    estoque = gerar_estoque(args.produtos)
    vendas = gerar_vendas(args.vendas, clientes, vendedores, estoque)
    crediario = gerar_crediario(vendas)
    promocoes = gerar_promocoes(args.promocoes, estoque)

    ids_cliente_validos = clientes["id_cliente"].tolist()

    print(f"Injetando falhas (taxa-erro={args.taxa_erro:.0%}) para simular dados de produção...")
    clientes = sujar_clientes(clientes, args.taxa_erro)
    estoque = sujar_estoque(estoque, args.taxa_erro)
    vendas = sujar_vendas(vendas, args.taxa_erro, ids_cliente_validos)
    crediario = sujar_crediario(crediario, args.taxa_erro)
    promocoes = sujar_promocoes(promocoes, args.taxa_erro)

    tabelas = {
        "clientes.csv": clientes,
        "vendedores.csv": vendedores,
        "estoque.csv": estoque,
        "vendas.csv": vendas,
        "crediario.csv": crediario,
        "promocoes.csv": promocoes,
    }

    for nome_arquivo, df in tabelas.items():
        caminho = os.path.join(args.output, nome_arquivo)
        df.to_csv(caminho, index=False)
        print(f"  {nome_arquivo:<16} {len(df):>6} linhas -> {caminho}")

    print("Massa de dados gerada com sucesso!")

    # --- Configurações de Conexão SFTP / SSH ---
    HOST_REMOTO = os.getenv("SFTP_HOST", "marcos@192.168.122.46")
    USUARIO_REMOTO = os.getenv("SFTP_USER", "marcos")
    SENHA_REMOTA = os.getenv("SFTP_PASS", None)        
    CHAVE_PRIVADA = os.getenv("SFTP_KEY", None)                   
    CAMINHO_REMOTO = "/opt/etl/brute_data"

    print("\nIniciando transferência SFTP dos arquivos .csv...")
    try:
        enviar_diretorio_sftp(
            diretorio_local=args.output,
            caminho_remoto=CAMINHO_REMOTO,
            host=HOST_REMOTO,
            usuario=USUARIO_REMOTO,
            senha=SENHA_REMOTA,
            chave_privada=CHAVE_PRIVADA,
            porta=22
        )
        print("Transferência SFTP concluída com sucesso!")
    except Exception as erro:
        print(f"Erro durante a transferência SFTP: {erro}")


if __name__ == "__main__":
    main()