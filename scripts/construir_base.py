"""Etapa 2: monta a base tratada em SQLite a partir dos CSV de dados/brutos/ e das consultas de sql/.

    python scripts/construir_base.py

Roda sql/00_esquema.sql, carrega os CSV nas tabelas stg_*, roda sql/10, 20 e 30 em ordem e exporta
as tabelas finais em CSV para dados/tratados/. O arquivo dados/tratados/amostra.sqlite é apagado e
refeito a cada execução: a base é derivada, e o que vale é o script.
"""
import csv
import os
import sqlite3

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(RAIZ, 'dados', 'brutos')
TRATADOS = os.path.join(RAIZ, 'dados', 'tratados')
SQL = os.path.join(RAIZ, 'sql')
BANCO = os.path.join(TRATADOS, 'amostra.sqlite')

# tabela, arquivo CSV (em dados/brutos/), colunas do CSV na ordem da tabela
CARGAS = [
    ('stg_municipio', 'municipios_sp.csv', ['cod_ibge', 'municipio', 'regiao_imediata', 'regiao_intermediaria']),
    ('stg_siconfi', 'siconfi_municipio_ano.csv',
     ['ano', 'cod_ibge', 'entregou_ic', 'entregou_ie', 'populacao', 'rc_bruta', 'ded_fundeb', 'outras_ded',
      'transf_correntes', 'saude_empenhada', 'educacao_empenhada']),
    ('stg_populacao_estimada', 'ibge_populacao_estimada.csv', ['cod_ibge', 'ano', 'populacao']),
    ('stg_populacao_censo2022', 'ibge_populacao_censo2022.csv', ['cod_ibge', 'ano', 'populacao']),
    ('stg_pib', 'ibge_pib_corrente_mil_reais.csv', ['cod_ibge', 'ano', 'pib_mil_reais']),
    ('stg_ipca', 'ibge_ipca_indice.csv', ['mes', 'indice']),
    ('stg_ideb', 'ideb_municipio_ano.csv', ['cod_ibge', 'ano', 'ideb_anos_iniciais_municipal']),
    ('stg_sinasc', 'sinasc_municipio_ano.csv',
     ['ano', 'cod_municipio6', 'nascidos', 'pre_natal_informado', 'pre_natal_7mais', 'parto_informado',
      'parto_cesareo']),
]

EXPORTACOES = [
    ('dim_municipio.csv', 'SELECT * FROM dim_municipio ORDER BY cod_ibge'),
    ('dim_indicador.csv', 'SELECT * FROM dim_indicador ORDER BY ordem'),
    ('indicadores_longo.csv',
     'SELECT f.cod_ibge, d.municipio, d.faixa_porte, f.ano, f.indicador_id, f.valor '
     'FROM fato_indicador f JOIN dim_municipio d ON d.cod_ibge = f.cod_ibge '
     'ORDER BY f.indicador_id, f.cod_ibge, f.ano'),
    ('referencia_faixa.csv', 'SELECT * FROM ref_faixa ORDER BY indicador_id, faixa_porte, ano'),
    ('populacao.csv', 'SELECT * FROM v_populacao ORDER BY cod_ibge, ano'),
    ('exclusoes_declaracao.csv', 'SELECT * FROM exclusao_declaracao ORDER BY cod_ibge, ano, campo'),
]


def rodar_sql(con, nome):
    with open(os.path.join(SQL, nome), encoding='utf-8') as f:
        con.executescript(f.read())


def carregar(con, tabela, arquivo, colunas):
    with open(os.path.join(BRUTOS, arquivo), encoding='utf-8', newline='') as f:
        leitor = csv.DictReader(f)
        linhas = [[(r[c] if r[c] != '' else None) for c in colunas] for r in leitor]
    marcas = ','.join('?' * len(colunas))
    con.executemany(f'INSERT INTO {tabela} VALUES ({marcas})', linhas)
    return len(linhas)


def exportar(con, arquivo, consulta):
    cur = con.execute(consulta)
    nomes = [c[0] for c in cur.description]
    with open(os.path.join(TRATADOS, arquivo), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(nomes)
        n = 0
        for linha in cur:
            w.writerow(linha)
            n += 1
    return n


def main():
    os.makedirs(TRATADOS, exist_ok=True)
    if os.path.exists(BANCO):
        os.remove(BANCO)
    con = sqlite3.connect(BANCO)
    rodar_sql(con, '00_esquema.sql')
    for tabela, arquivo, colunas in CARGAS:
        print(f'{tabela}: {carregar(con, tabela, arquivo, colunas)} linhas')
    for nome in ('10_dimensoes.sql', '20_indicadores.sql', '30_referencia.sql'):
        rodar_sql(con, nome)
    con.commit()
    for arquivo, consulta in EXPORTACOES:
        print(f'{arquivo}: {exportar(con, arquivo, consulta)} linhas')
    con.close()


if __name__ == '__main__':
    main()
