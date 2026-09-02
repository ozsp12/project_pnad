"""Build PNAD metadata for the 1976–2025 longitudinal income dataset.

This module is derived from the refactored ``00_cria_metadata`` notebook.
It centralizes annual extraction specifications, raw-file ingestion metadata,
currency/exchange-rate information, and CPI-based normalization factors.
"""

from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.xlsx"

# define função para construir o dataframe de especificações
def build_specs_pnad_df(): 
    # dicionário com metadados por ano (variáveis, posições e links)
    specs_pnad = {  
        1976: ('V2954', 227, 9, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1976/'),
        1977: ('V131', 288, 9, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1977/'),
        1978: ('V2541', 214, 9, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1978/'),
        1979: ('V2517', 167, 9, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1979/'),
        1980: (None, None, None, None, None, None, None),
        1981: ('V5010', 223, 7, 'V9329', 219, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1981/'),
        1982: ('V602', 199, 7, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1982/'),
        1983: ('V5010', 223, 7, 'V9329', 219, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1983/'),
        1984: ('V5010', 223, 7, 'V9329', 219, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1984/'),
        1985: ('V5010', 248, 9, 'V9329', 244, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1985/'),
        1986: ('V5010', 256, 9, 'V9329', 252, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1986/'),
        1987: ('V5010', 248, 9, 'V9329', 244, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1987/'),
        1988: ('V5010', 248, 9, 'V9329', 244, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1988/'),
        1989: ('V5010', 60, 9, 'V9329', 245, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1989/'),
        1990: ('V5010', 56, 9, 'V9329', 244, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1990/PND1990N.DAT'),
        1991: (None, None, None, None, None, None, None),
        1992: ('V4614', 139, 12, 'V0105', 15, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1992/'),
        1993: ('V4614', 139, 12, 'V0105', 15, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1993/'),
        1994: (None, None, None, None, None, None, None),
        1995: ('V4614', 139, 12, 'V0105', 15, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1995/'),
        1996: ('V4614', 139, 12, 'V0105', 15, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1996/'),
        1997: ('V4614', 139, 12, 'V0105', 15, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1997/'),
        1998: ('V4614', 142, 12, 'V0105', 15, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1998/'),
        1999: ('V4614', 142, 12, 'V0105', 15, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/1999/'),
        2000: (None, None, None, None, None, None, None),
        2001: ('V4614', 146, 12, 'V0105', 17, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2001.zip'),
        2002: ('V4614', 153, 12, 'V0105', 17, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2002.zip'),
        2003: ('V4614', 153, 12, 'V0105', 17, 2, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2003_20150814.zip'),
        2004: ('V4621', 239, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2004.zip'),
        2005: ('V4621', 181, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2005.zip'),
        2006: ('V4621', 181, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2006.zip'),
        2007: ('V4621', 179, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2007_20150814.zip'),
        2008: ('V4621', 181, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2008.zip'),
        2009: ('V4621', 181, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2009_20171228.zip'),
        2010: (None, None, None, None, None, None, None),
        2011: ('V4621', 176, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2011_20150814.zip'),
        2012: ('V4621', 176, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/reponderacao_2001_2012/PNAD_reponderado_2012_20150814.zip'),
        2013: ('V4621', 193, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/2013/Dados_20170807.zip'),
        2014: ('V4621', 193, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/2014/Dados_20170323.zip'),
        2015: ('V4621', 193, 12, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/2015/Dados_20170517.zip'),
        2016: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2016/'),
        2017: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2017/'),
        2018: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2018/'),
        2019: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2019/'),
        2020: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2020/'),
        2021: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2021/'),
        2022: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2022/'),
        2023: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2023/'),
        2024: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2024/'),
        2025: ('VD4019', 443, 8, None, None, None, 'https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/2025/')
    }  
    # define nomes das colunas
    cols = ['var_renda','pos_renda','tam_renda','var_morador','pos_morador','tam_morador','link']  
    # cria dataframe a partir do dicionário
    df = pd.DataFrame.from_dict(specs_pnad, orient='index', columns=cols) 
    # transforma índice em coluna ano
    df = df.reset_index().rename(columns={'index':'ano'})  
    # especificações de ingestão dos arquivos brutos
    available = df['pos_renda'].notna()

    df['raw_subdir'] = ''
    df.loc[df['ano'].isin([1983, 1988]), 'raw_subdir'] = df.loc[
        df['ano'].isin([1983, 1988]), 'ano'
    ].astype(str)

    df['raw_pattern'] = ''
    df.loc[available, 'raw_pattern'] = (
        'DOM' + df.loc[available, 'ano'].astype(str) + '.*'
    )
    df.loc[df['ano'] == 1983, 'raw_pattern'] = 'PND83RM*.DAT'
    df.loc[df['ano'] == 1988, 'raw_pattern'] = 'PND88RM*.DAT'

    df['n_files'] = 0
    df.loc[available, 'n_files'] = 1
    df.loc[df['ano'].isin([1983, 1988]), 'n_files'] = 8

    df['missing_renda'] = np.nan
    df.loc[df['ano'].between(1977, 1990) & available, 'missing_renda'] = 999_999_999
    df.loc[df['ano'].between(1992, 2015) & available, 'missing_renda'] = 999_999_999_999
    df.loc[df['ano'].between(2016, 2025) & available, 'missing_renda'] = 99_999_999
    df.loc[df['ano'].isin([1976, 1981, 1982, 1983, 1984]), 'missing_renda'] = 9_999_999

    # campos textuais vazios para anos sem pesquisa
    df['link'] = df['link'].fillna('')
    df['raw_subdir'] = df['raw_subdir'].fillna('')
    df['raw_pattern'] = df['raw_pattern'].fillna('')

    # ordena por ano e reseta índice
    df = df.sort_values('ano').reset_index(drop=True)
    return df


def build_currency_df():
    """Build currency, exchange-rate, and CPI adjustment metadata."""
    df_currency = pd.DataFrame({
        "Year": list(range(1976, 2026)),
        "Currency": [
            "cruzeiro-Cr$", "cruzeiro-Cr$", "cruzeiro-Cr$", "cruzeiro-Cr$", "cruzeiro-Cr$",
            "cruzeiro-Cr$", "cruzeiro-Cr$", "cruzeiro-Cr$", "cruzeiro-Cr$", "cruzeiro-Cr$",
            "cruzado-Cz$", "cruzado-Cz$", "cruzado-Cz$", "cruzado novo-NCz$", "cruzeiro-Cr$",
            "cruzeiro-Cr$", "cruzeiro-Cr$", "cruzeiro real-CR$", "Real R$", "Real R$",
            "Real R$", "Real R$", "Real R$", "Real R$", "Real R$",
            "Real R$", "Real R$", "Real R$", "Real R$", "Real R$",
            "Real R$", "Real R$", "Real R$", "Real R$", "Real R$",
            "Real R$", "Real R$", "Real R$", "Real R$", "Real R$",
            "Real R$", "Real R$", "Real R$", "Real R$", "Real R$",
            "Real R$", "Real R$", "Real R$", "Real R$", "Real R$"
        ],
        "Exchange": [
            11.3130, 14.9300, 19.0500, 28.7920, np.nan,
            105.2840, 202.0880, 701.3810, 2203.9470, 7461.6670,
            13.8400, 49.8660, 326.2350, 3.2670, 75.5410,
            np.nan, 5771.5240, 111.1890, np.nan, 0.9528,
            1.0193, 1.0936, 1.1809, 1.8981, np.nan,
            2.6717, 3.3420, 2.9228, 2.8911, 2.2944,
            2.1687, 1.8996, 1.7996, 1.8198, np.nan,
            1.7498, 2.0281, 2.2705, 2.3329, 3.9065,
            3.2564, 3.1348, 4.1165, 4.1215, 5.3995,
            5.2797, 5.2370, 4.9370, 5.5416, 5.3674
        ],
        "Index": [
            100.00000, 106.42361, 115.45139, 129.16667, np.nan,
            161.63194, 169.61806, 174.30556, 181.77083, 187.67361,
            190.97222, 199.13194, 207.46528, 216.66667, 230.03472,
            np.nan, 244.96528, 251.73611, np.nan, 265.79861,
            273.78472, 279.86111, 283.85417, 291.31944, np.nan,
            309.20139, 313.88889, 321.35417, 329.51389, 345.13889,
            352.08333, 362.06076, 379.99479, 374.75868, np.nan,
            393.39757, 401.06771, 405.45833, 412.28646, 412.32292,
            418.70833, 427.83854, 437.81597, 445.19097, 451.38368,
            475.53819, 514.49479, 533.46528, 546.40972, 562.92535
        ]
    })

    idx_2025 = df_currency.loc[df_currency["Year"] == 2025, "Index"].iloc[0]
    mask = df_currency["Index"].notna()
    df_currency.loc[mask, "Adjust2025"] = (idx_2025 / df_currency.loc[mask, "Index"]) - 1
    df_currency.loc[mask, "Inflation"] = df_currency.loc[mask, "Adjust2025"] + 1
    return df_currency


def build_metadata_df():
    """Merge PNAD extraction specifications with monetary normalization metadata."""
    df_specs = build_specs_pnad_df()

    available = df_specs["pos_renda"].notna()
    assert (df_specs.loc[available, "raw_pattern"] != "").all()
    assert (df_specs.loc[available, "n_files"] > 0).all()
    assert df_specs.loc[available, "missing_renda"].notna().all()

    df_currency = build_currency_df()

    df_metadata = (
        df_specs
        .merge(df_currency, left_on="ano", right_on="Year", how="left")
        .drop(columns="Year")
    )

    assert df_metadata["ano"].is_unique
    assert df_metadata["ano"].tolist() == list(range(1976, 2026))

    return df_metadata


def save_metadata(df_metadata, output_path=DEFAULT_OUTPUT_PATH):
    """Save ``df_metadata`` to the repository metadata directory."""
    output_path = Path(output_path)
    if not output_path.parent.is_dir():
        raise FileNotFoundError(
            f"Pasta de metadata não encontrada: {output_path.parent}"
        )

    df_metadata.to_excel(output_path, index=False)
    return output_path


def main(output_path=DEFAULT_OUTPUT_PATH):
    """Build, validate, and save ``df_metadata``."""
    df_metadata = build_metadata_df()
    output_path = save_metadata(df_metadata, output_path)
    return df_metadata, output_path


if __name__ == "__main__":
    df_metadata, output_path = main()
    print(f"df_metadata saved to: {output_path}")
    print(df_metadata)
