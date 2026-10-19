from datetime import datetime, timedelta
import random

import pandas as pd

MOJIBAKE = {
    "á": "Ã¡", "ã": "Ã£", "â": "Ã¢", "à": "Ã ", "é": "Ã©", "ê": "Ãª",
    "í": "Ã­", "ó": "Ã³", "õ": "Ãµ", "ô": "Ã´", "ú": "Ãº", "ç": "Ã§",
}

def data_aleatoria(inicio: datetime, fim: datetime) -> datetime:
    delta_dias = (fim - inicio).days
    return inicio + timedelta(days=random.randint(0, max(delta_dias, 0)))

def sujar_case(valor: str) -> str:
    """Bagunça a caixa do texto: TUDO MAIÚSCULO, tudo minúsculo ou Title Case."""
    if not isinstance(valor, str):
        return valor
    return random.choice([valor.upper(), valor.lower(), valor.title()])


def sujar_espacos(valor: str) -> str:
    """Adiciona espaços em branco extras no início/fim (erro comum de import de planilha)."""
    if not isinstance(valor, str):
        return valor
    return random.choice([f" {valor}", f"{valor}  ", f" {valor} "])


def sujar_encoding(valor: str) -> str:
    """Simula acentuação corrompida por mismatch de encoding (UTF-8 lido como Latin-1)."""
    if not isinstance(valor, str):
        return valor
    for original, quebrado in MOJIBAKE.items():
        valor = valor.replace(original, quebrado)
    return valor


def sujar_data_formato(data_iso: str) -> str:
    """Converte uma data ISO (yyyy-mm-dd) para um formato alternativo (dd/mm/yyyy ou dd-mm-yyyy)."""
    try:
        dt = datetime.strptime(str(data_iso), "%Y-%m-%d")
    except (ValueError, TypeError):
        return data_iso
    formato = random.choice(["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"])
    return dt.strftime(formato)


def sujar_numero_como_texto_brl(valor: float) -> str:
    """Transforma um número em texto com formatação monetária BR (vírgula decimal, 'R$')."""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return random.choice([texto, f"R$ {texto}"])


def sujar_id_com_prefixo(id_valor, prefixo: str) -> str:
    """Transforma um ID numérico puro em texto com prefixo (ex.: 123 -> 'CLI-0123')."""
    return f"{prefixo}-{int(id_valor):04d}"


def id_fk_quebrada(ids_validos: list, deslocamento: int = 100000):
    """Gera uma FK 'órfã': um ID que não existe na tabela de origem."""
    return max(ids_validos) + random.randint(1, deslocamento)


def amostra_indices(df: pd.DataFrame, taxa: float) -> pd.Index:
    """Sorteia uma amostra de índices do dataframe, do tamanho de `taxa`."""
    n = max(int(len(df) * taxa), 0)
    if n == 0:
        return pd.Index([])
    return pd.Index(random.sample(list(df.index), min(n, len(df))))


def duplicar_linhas(df: pd.DataFrame, taxa: float, quase: bool = False,
                     coluna_variacao: str = None) -> pd.DataFrame:
    """
    Duplica uma fração das linhas do dataframe, simulando reprocessamento/
    reingestão de eventos (um problema clássico em pipelines de streaming
    e em cargas de ETL reexecutadas).

    Se `quase=True`, a cópia mantém a mesma chave primária mas altera um
    valor em `coluna_variacao` -- simulando o caso, ainda mais traiçoeiro,
    de duas linhas com a MESMA chave e valores DIFERENTES (conflito de
    reconciliação).
    """
    idx = amostra_indices(df, taxa)
    if len(idx) == 0:
        return df
    copiadas = df.loc[idx].copy()
    if quase and coluna_variacao in df.columns:
        if pd.api.types.is_numeric_dtype(df[coluna_variacao]):
            copiadas[coluna_variacao] = copiadas[coluna_variacao] * random.uniform(0.9, 1.1)
            copiadas[coluna_variacao] = copiadas[coluna_variacao].round(2)
        else:
            copiadas[coluna_variacao] = copiadas[coluna_variacao].apply(sujar_case)
    return pd.concat([df, copiadas], ignore_index=True)


def aplicar_em_amostra(df: pd.DataFrame, coluna: str, funcao, taxa: float):
    """Aplica `funcao` sobre uma amostra aleatória de `taxa` linhas da coluna, in-place."""
    idx = amostra_indices(df, taxa)
    if len(idx) == 0:
        return
    df[coluna] = df[coluna].astype(object)
    df.loc[idx, coluna] = df.loc[idx, coluna].apply(funcao)


def nulificar_amostra(df: pd.DataFrame, coluna: str, taxa: float, como_vazio: bool = False):
    """Zera uma amostra de valores da coluna (NaN, ou string vazia -- os dois aparecem em bases reais)."""
    idx = amostra_indices(df, taxa)
    if len(idx) == 0:
        return
    df[coluna] = df[coluna].astype(object)
    df.loc[idx, coluna] = "" if como_vazio else None