import os
import re
import numpy as np
import pandas as pd

# Diretórios de origem e destino
INPUT_DIR = "./DA/datalake/raw_data"
OUTPUT_DIR = "./DA/datalake/clean_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fix_mojibake_and_strip(text):
    """Corrige codificação corrompida (mojibake) e remove espaços nas extremidades."""
    if pd.isna(text):
        return text
    s = str(text).strip()
    mojibake_map = {
        'AguaÃ\xad': 'Aguaí',
        'TambaÃº': 'Tambaú',
        'SÃ£o JosÃ© do Rio Pardo': 'São José do Rio Pardo',
        'acessório': 'Acessório',
        'jaqueta': 'Jaqueta',
        'BLUSA': 'Blusa',
        'JAQUETA': 'Jaqueta',
        'gg': 'GG',
    }
    if s in mojibake_map:
        return mojibake_map[s]
    try:
        if 'Ã' in s or 'Â' in s:
            s = s.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return s

def parse_mixed_date(series):
    """Padroniza datas com múltiplos formatos para o padrão ISO (YYYY-MM-DD)."""
    return pd.to_datetime(series, format='mixed', errors='coerce').dt.strftime('%Y-%m-%d')

def clean_currency_to_float(val):
    """Converte valores monetários/numéricos legados para float64."""
    if pd.isna(val):
        return np.nan
    s = str(val).replace('R$', '').strip()
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return np.nan

def clean_clientes():
    df = pd.read_csv(os.path.join(INPUT_DIR, 'clientes.csv'))
    
    # 1. Tratamento de Strings e Codificação
    df['cidade'] = df['cidade'].apply(fix_mojibake_and_strip)
    df['canal_preferencial'] = df['canal_preferencial'].apply(fix_mojibake_and_strip).str.capitalize()
    
    # 2. Padronização de Datas
    df['data_cadastro'] = parse_mixed_date(df['data_cadastro'])
    
    # 3. Tratamento de Outliers/Anomalias em Idade
    valid_age_median = df.loc[(df['idade'] >= 18) & (df['idade'] <= 99), 'idade'].median()
    df['idade'] = np.where((df['idade'] < 18) | (df['idade'] > 99), valid_age_median, df['idade']).astype(int)
    
    # 4. Tipagem
    df['id_cliente'] = df['id_cliente'].astype(int)
    
    df.to_csv(os.path.join(OUTPUT_DIR, 'clientes.csv'), index=False)
    print("✔ clientes.csv limpo e salvo.")

def clean_crediario():
    df = pd.read_csv(os.path.join(INPUT_DIR, 'crediario.csv'))
    
    # 1. Padronização de Datas
    df['data_vencimento'] = parse_mixed_date(df['data_vencimento'])
    df['data_pagamento'] = parse_mixed_date(df['data_pagamento'])
    
    # 2. Tratamento de Strings
    df['status'] = df['status'].apply(fix_mojibake_and_strip)
    
    # 3. Tipagem e Arredondamento
    df['valor_parcela'] = df['valor_parcela'].round(2)
    df['valor_em_aberto'] = df['valor_em_aberto'].round(2)
    df['dias_atraso'] = df['dias_atraso'].astype(int)
    
    df.to_csv(os.path.join(OUTPUT_DIR, 'crediario.csv'), index=False)
    print("✔ crediario.csv limpo e salvo.")

def clean_estoque():
    df = pd.read_csv(os.path.join(INPUT_DIR, 'estoque.csv'))
    
    # 1. Tratamento de Strings e Tamanhos
    df['categoria'] = df['categoria'].apply(fix_mojibake_and_strip).str.title()
    df['cor'] = df['cor'].apply(fix_mojibake_and_strip).str.capitalize()
    df['produto'] = df['produto'].apply(fix_mojibake_and_strip)
    df['tamanho'] = df['tamanho'].apply(fix_mojibake_and_strip).str.upper()
    df['tamanho'] = df['tamanho'].replace({'0': np.nan})
    
    # 2. Conversão de Moeda
    df['preco_unitario'] = df['preco_unitario'].apply(clean_currency_to_float).round(2)
    
    # 3. Correção de Quantidades Negativas (Inversão de Sinal)
    df['quantidade_saida'] = df['quantidade_saida'].abs().astype(int)
    df['quantidade_entrada'] = df['quantidade_entrada'].astype(int)
    
    # 4. Padronização de Datas
    df['data_entrada'] = parse_mixed_date(df['data_entrada'])
    df['ultima_venda'] = parse_mixed_date(df['ultima_venda'])
    
    df.to_csv(os.path.join(OUTPUT_DIR, 'estoque.csv'), index=False)
    print("✔ estoque.csv limpo e salvo.")

def clean_promocoes():
    df = pd.read_csv(os.path.join(INPUT_DIR, 'promocoes.csv'))
    
    # 1. Tratamento de Texto
    df['categoria'] = df['categoria'].apply(fix_mojibake_and_strip).str.title()
    df['produto'] = df['produto'].apply(fix_mojibake_and_strip)
    df['tipo_desconto'] = df['tipo_desconto'].apply(fix_mojibake_and_strip)
    
    # 2. Padronização de Datas
    df['data_inicio'] = parse_mixed_date(df['data_inicio'])
    df['data_fim'] = parse_mixed_date(df['data_fim'])
    
    # 3. Métricas
    df['desconto'] = df['desconto'].round(4)
    
    df.to_csv(os.path.join(OUTPUT_DIR, 'promocoes.csv'), index=False)
    print("✔ promocoes.csv limpo e salvo.")

def clean_vendas():
    df = pd.read_csv(os.path.join(INPUT_DIR, 'vendas.csv'))
    
    # 1. Tratamento de Strings e Tamanhos
    df['canal'] = df['canal'].apply(fix_mojibake_and_strip)
    df['categoria'] = df['categoria'].apply(fix_mojibake_and_strip).str.title()
    df['cor'] = df['cor'].apply(fix_mojibake_and_strip).str.capitalize()
    df['forma_pagamento'] = df['forma_pagamento'].apply(fix_mojibake_and_strip)
    df['produto'] = df['produto'].apply(fix_mojibake_and_strip)
    df['tamanho'] = df['tamanho'].apply(fix_mojibake_and_strip).str.upper()
    df['tamanho'] = df['tamanho'].replace({'0': np.nan})
    
    # 2. Padronização de Data e Hora
    df['data_venda'] = parse_mixed_date(df['data_venda'])
    
    # 3. Tipagem de Chaves Estrangeiras Nulas (ex: cliente não identificado)
    df['id_cliente'] = df['id_cliente'].astype('Int64')
    df['id_produto'] = df['id_produto'].astype(int)
    df['id_venda'] = df['id_venda'].astype(int)
    df['id_vendedor'] = df['id_vendedor'].astype(int)
    
    # 4. Valores Numéricos
    df['preco_unitario'] = df['preco_unitario'].round(2)
    df['desconto'] = df['desconto'].round(2)
    df['valor_total'] = df['valor_total'].round(2)
    
    df.to_csv(os.path.join(OUTPUT_DIR, 'vendas.csv'), index=False)
    print("✔ vendas.csv limpo e salvo.")

def clean_vendedores():
    df = pd.read_csv(os.path.join(INPUT_DIR, 'vendedores.csv'))
    
    # 1. Tratamento de Texto
    df['nome'] = df['nome'].apply(fix_mojibake_and_strip)
    df['cidade_loja'] = df['cidade_loja'].apply(fix_mojibake_and_strip)
    
    # 2. Padronização de Datas
    df['data_contratacao'] = parse_mixed_date(df['data_contratacao'])
    
    # 3. Métricas Numéricas
    df['meta_mensal'] = df['meta_mensal'].round(2)
    df['id_vendedor'] = df['id_vendedor'].astype(int)
    
    df.to_csv(os.path.join(OUTPUT_DIR, 'vendedores.csv'), index=False)
    print("✔ vendedores.csv limpo e salvo.")

if __name__ == "__main__":
    print("Iniciando processo de higienização do Datalake...\n")
    clean_clientes()
    clean_crediario()
    clean_estoque()
    clean_promocoes()
    clean_vendas()
    clean_vendedores()
    print(f"\nProcessamento concluído. Arquivos salvos em: {OUTPUT_DIR}")