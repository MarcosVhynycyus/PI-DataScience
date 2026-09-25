from datetime import datetime, timedelta
from faker import Faker
import random
import pandas as pd

from quebras import amostra_indices, aplicar_em_amostra, data_aleatoria, duplicar_linhas, id_fk_quebrada, sujar_case, sujar_data_formato, sujar_encoding, sujar_espacos, sujar_numero_como_texto_brl

fake = Faker("pt_BR")

CIDADES = [
    "Tambaú", "Mococa", "Vargem Grande do Sul", "São João da Boa Vista",
    "Aguaí", "Casa Branca", "São José do Rio Pardo", "Itobi",
]
CANAIS = ["Online", "Física"]
CATEGORIAS = ["Camiseta", "Blusa", "Bermuda", "Jaqueta", "Calça", "Acessório", "Vestido"]
VARIACOES_PRODUTO = ["Slim", "Premium", "Básica", "Casual", "Esporte", "Social", "X"]
CORES = ["Verde", "Rosa", "Branca", "Preta", "Vermelha", "Azul", "Cinza"]
TAMANHOS = ["P", "M", "G", "GG"]
FORMAS_PAGAMENTO = ["Cartão de Débito", "Cartão de Crédito", "PIX", "Dinheiro", "Crediário"]
PESOS_FORMA_PAGAMENTO = [0.28, 0.27, 0.22, 0.13, 0.10]  # crediário é minoritário, como no varejo real
STATUS_PARCELA = ["Pago", "Em aberto", "Atrasado"]

DATA_BASE = datetime(2024, 1, 1)
HOJE = datetime.now()

def gerar_clientes(n: int) -> pd.DataFrame:
    linhas = []
    for id_cliente in range(1, n + 1):
        linhas.append({
            "id_cliente": id_cliente,
            "idade": random.randint(16, 75),
            "cidade": random.choice(CIDADES),
            "data_cadastro": data_aleatoria(DATA_BASE, HOJE).strftime("%Y-%m-%d"),
            "canal_preferencial": random.choice(CANAIS),
        })
    return pd.DataFrame(linhas)


def gerar_vendedores(n: int) -> pd.DataFrame:
    linhas = []
    for id_vendedor in range(1, n + 1):
        contratacao = data_aleatoria(DATA_BASE, HOJE)
        linhas.append({
            "id_vendedor": id_vendedor,
            "nome": fake.name(),
            "cidade_loja": random.choice(CIDADES),
            "data_contratacao": contratacao.strftime("%Y-%m-%d"),
            "meta_mensal": round(random.uniform(8000, 30000), 2),
        })
    return pd.DataFrame(linhas)


def gerar_estoque(n: int) -> pd.DataFrame:
    linhas = []
    for id_produto in range(1, n + 1):
        categoria = random.choice(CATEGORIAS)
        produto = f"{categoria} {random.choice(VARIACOES_PRODUTO)}"
        entrada = random.randint(20, 150)
        saida = random.randint(0, entrada + 40)
        # "Estoque contábil" (entrada - saída, sem deixar negativo)
        estoque_atual = max(entrada - saida, 0)
        # "Estoque físico" (contagem real) -- propositalmente pode divergir
        # do contábil, simulando quebra/perda/furto, um problema real de
        # conciliação de estoque em qualquer ERP de varejo.
        estoque_fisico = max(estoque_atual + random.randint(-3, 3), 0)
        data_entrada = data_aleatoria(DATA_BASE, HOJE)
        linhas.append({
            "id_produto": id_produto,
            "categoria": categoria,
            "produto": produto,
            "cor": random.choice(CORES),
            "tamanho": random.choice(TAMANHOS),
            "preco_unitario": round(random.uniform(25.0, 350.0), 2),
            "estoque_minimo": random.randint(3, 10),
            "estoque_maximo": random.randint(20, 40),
            "quantidade_entrada": entrada,
            "quantidade_saida": saida,
            "estoque_atual": estoque_atual,
            "estoque_fisico": estoque_fisico,
            "data_entrada": data_entrada.strftime("%Y-%m-%d"),
            "ultima_venda": data_aleatoria(data_entrada, HOJE).strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(linhas)


def gerar_vendas(n: int, clientes: pd.DataFrame, vendedores: pd.DataFrame,
                  estoque: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    ids_cliente = clientes["id_cliente"].tolist()
    ids_vendedor = vendedores["id_vendedor"].tolist()
    produtos_idx = estoque.set_index("id_produto")

    for id_venda in range(1, n + 1):
        produto_row = produtos_idx.loc[random.choice(produtos_idx.index)]
        quantidade = random.randint(1, 4)
        preco_unitario = produto_row["preco_unitario"]
        desconto = round(preco_unitario * quantidade * random.choice([0, 0, 0, 0.05, 0.1, 0.15]), 2)
        valor_total = round(preco_unitario * quantidade - desconto, 2)
        data_venda = data_aleatoria(datetime(2026, 3, 1), HOJE)

        # ~6% das vendas sem cliente identificado (venda avulsa / balcão),
        # proporção compatível com a observada no vendas.csv original.
        id_cliente = random.choice(ids_cliente) if random.random() > 0.06 else None

        linhas.append({
            "id_venda": id_venda,
            "data_venda": data_venda.strftime("%Y-%m-%d"),
            "hora_venda": f"{random.randint(9, 21):02d}:{random.choice(['00', '15', '30', '45'])}",
            "id_produto": produto_row.name,
            "produto": produto_row["produto"],
            "categoria": produto_row["categoria"],
            "cor": produto_row["cor"],
            "tamanho": produto_row["tamanho"],
            "quantidade": quantidade,
            "preco_unitario": preco_unitario,
            "desconto": desconto,
            "valor_total": valor_total,
            "forma_pagamento": random.choices(FORMAS_PAGAMENTO, weights=PESOS_FORMA_PAGAMENTO, k=1)[0],
            "canal": random.choice(CANAIS),
            "id_cliente": id_cliente,
            "id_vendedor": random.choice(ids_vendedor),
        })
    return pd.DataFrame(linhas)


def gerar_crediario(vendas: pd.DataFrame) -> pd.DataFrame:
    """
    Gera as parcelas de crediário a partir das vendas cuja forma de
    pagamento é 'Crediário'. Mantém FK explícita para id_venda e id_cliente
    -- reforçando o relacionamento entre tabelas pedido no enunciado.
    """
    linhas = []
    id_parcela = 1
    vendas_crediario = vendas[
        (vendas["forma_pagamento"] == "Crediário") & (vendas["id_cliente"].notna())
    ]

    for _, venda in vendas_crediario.iterrows():
        n_parcelas = random.randint(1, 4)
        valor_parcela = round(venda["valor_total"] / n_parcelas, 2)
        data_venda = datetime.strptime(venda["data_venda"], "%Y-%m-%d")

        for parcela_num in range(1, n_parcelas + 1):
            vencimento = data_venda + timedelta(days=30 * parcela_num)

            if vencimento > HOJE:
                status = "Em aberto"
                dias_atraso = 0
                data_pagamento = None
            else:
                # a maioria paga em dia, uma fração atrasa
                if random.random() < 0.8:
                    status = "Pago"
                    dias_atraso = 0
                    data_pagamento = (vencimento + timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d")
                else:
                    dias_atraso = random.randint(1, 45)
                    if dias_atraso > 30 and random.random() < 0.5:
                        status = "Atrasado"
                        data_pagamento = None
                    else:
                        status = "Pago"
                        data_pagamento = (vencimento + timedelta(days=dias_atraso)).strftime("%Y-%m-%d")

            valor_em_aberto = 0.0 if status == "Pago" else valor_parcela

            linhas.append({
                "id_parcela": id_parcela,
                "id_venda": int(venda["id_venda"]),
                "id_cliente": int(venda["id_cliente"]),
                "valor_parcela": valor_parcela,
                "data_vencimento": vencimento.strftime("%Y-%m-%d"),
                "dias_atraso": dias_atraso,
                "data_pagamento": data_pagamento,
                "status": status,
                "valor_em_aberto": valor_em_aberto,
            })
            id_parcela += 1
    return pd.DataFrame(linhas)


def gerar_promocoes(n: int, estoque: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    amostra_produtos = estoque.sample(min(n, len(estoque)), replace=n > len(estoque))
    for id_promocao, (_, produto_row) in enumerate(amostra_produtos.iterrows(), start=1):
        inicio = data_aleatoria(datetime(2026, 3, 1), HOJE)
        fim = inicio + timedelta(days=random.randint(5, 20))
        vendas_antes = random.randint(10, 60)
        linhas.append({
            "id_promocao": id_promocao,
            "produto": produto_row["produto"],
            "categoria": produto_row["categoria"],
            "tipo_desconto": random.choice(["Percentual", "Valor Fixo"]),
            "desconto": round(random.uniform(0.1, 0.35), 2),
            "data_inicio": inicio.strftime("%Y-%m-%d"),
            "data_fim": fim.strftime("%Y-%m-%d"),
            "vendas_antes": vendas_antes,
            "vendas_durante": int(vendas_antes * random.uniform(1.3, 2.5)),
        })
    return pd.DataFrame(linhas)

def sujar_clientes(df: pd.DataFrame, taxa: float) -> pd.DataFrame:
    df = duplicar_linhas(df, taxa / 2)                       # registro duplicado (reingestão)
    aplicar_em_amostra(df, "cidade", sujar_encoding, taxa)    # encoding quebrado
    aplicar_em_amostra(df, "canal_preferencial", sujar_case, taxa)  # 'ONLINE' / 'online' / 'Online'
    aplicar_em_amostra(df, "data_cadastro", sujar_data_formato, taxa)  # formato de data trocado
    # idades absurdas (erro de digitação/captura)
    idx = amostra_indices(df, taxa / 2)
    df.loc[idx, "idade"] = df.loc[idx, "idade"].apply(lambda x: random.choice([-1, 0, 150, 999]))
    return df


def sujar_estoque(df: pd.DataFrame, taxa: float) -> pd.DataFrame:
    df = duplicar_linhas(df, taxa / 3, quase=True, coluna_variacao="preco_unitario")
    aplicar_em_amostra(df, "cor", sujar_espacos, taxa)
    aplicar_em_amostra(df, "categoria", sujar_case, taxa)
    aplicar_em_amostra(df, "preco_unitario", sujar_numero_como_texto_brl, taxa)
    # tamanhos fora do domínio (ex.: erro de cadastro manual)
    idx = amostra_indices(df, taxa / 2)
    df.loc[idx, "tamanho"] = [random.choice(["GGG", "XXXG", "0", "gg", " M"]) for _ in idx]
    # quantidade de saída negativa (estorno mal tratado)
    idx = amostra_indices(df, taxa / 4)
    df.loc[idx, "quantidade_saida"] = -df.loc[idx, "quantidade_saida"]
    return df


def sujar_vendas(df: pd.DataFrame, taxa: float, ids_cliente_validos: list) -> pd.DataFrame:
    df = duplicar_linhas(df, taxa / 2)                                  # evento duplicado
    aplicar_em_amostra(df, "forma_pagamento", sujar_case, taxa)         # 'pix' / 'PIX' / 'DINHEIRO'
    aplicar_em_amostra(df, "forma_pagamento",
                        lambda v: v.replace("Cartão de Crédito", "cartao credito") if isinstance(v, str) else v,
                        taxa / 3)                                       # sem acento e com espaço
    aplicar_em_amostra(df, "hora_venda", sujar_espacos, taxa)
    aplicar_em_amostra(df, "data_venda", sujar_data_formato, taxa)      # dd/mm/yyyy misturado com yyyy-mm-dd

    # FK quebrada: id_produto que não existe na tabela de estoque
    idx = amostra_indices(df, taxa / 4)
    df.loc[idx, "id_produto"] = [id_fk_quebrada(df["id_produto"].tolist()) for _ in idx]

    # FK "solta": id_cliente que não existe em clientes.csv (ex.: cliente excluído/migrado)
    idx = amostra_indices(df, taxa / 4)
    df.loc[idx, "id_cliente"] = [id_fk_quebrada(ids_cliente_validos) for _ in idx]

    # quantidade zero/negativa (erro de PDV)
    idx = amostra_indices(df, taxa / 4)
    df.loc[idx, "quantidade"] = df.loc[idx, "quantidade"].apply(lambda x: random.choice([0, -1, -2]))

    # desconto maior que o valor da venda (regra de negócio violada) -- calculado
    # ANTES de "sujar_numero_como_texto_brl" em valor_total, para não misturar
    # tipos (texto x número) na mesma operação aritmética.
    idx = amostra_indices(df, taxa / 6)
    df.loc[idx, "desconto"] = pd.to_numeric(df.loc[idx, "valor_total"], errors="coerce") * random.uniform(1.2, 2.0)

    # número formatado como texto monetário BR (aplicado por último: depois
    # disso a coluna passa a ter tipos mistos, propositalmente)
    aplicar_em_amostra(df, "valor_total", sujar_numero_como_texto_brl, taxa)
    return df


def sujar_crediario(df: pd.DataFrame, taxa: float) -> pd.DataFrame:
    if df.empty:
        return df
    df = duplicar_linhas(df, taxa / 2)
    aplicar_em_amostra(df, "status", sujar_case, taxa)
    aplicar_em_amostra(df, "data_vencimento", sujar_data_formato, taxa)
    # valor_em_aberto inconsistente com status (ex.: marcado 'Pago' mas ainda com saldo)
    idx = amostra_indices(df, taxa / 4)
    df.loc[idx, "valor_em_aberto"] = df.loc[idx, "valor_parcela"]
    # dias_atraso negativo (erro de cálculo de data)
    idx = amostra_indices(df, taxa / 6)
    df.loc[idx, "dias_atraso"] = -df.loc[idx, "dias_atraso"].abs() - 1
    return df


def sujar_promocoes(df: pd.DataFrame, taxa: float) -> pd.DataFrame:
    df = duplicar_linhas(df, taxa)
    aplicar_em_amostra(df, "tipo_desconto", sujar_case, taxa)
    # datas de promoção invertidas (fim antes do início)
    idx = amostra_indices(df, taxa / 3)
    df.loc[idx, ["data_inicio", "data_fim"]] = df.loc[idx, ["data_fim", "data_inicio"]].values
    return df