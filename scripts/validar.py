"""Etapa 4: confere a base com uma segunda implementação, escrita em pandas, sem olhar o SQL.

    python scripts/validar.py

Cada Indicador é refeito do CSV bruto com pandas e comparado, linha a linha, com o que as consultas
SQL gravaram. Os quartis por faixa são refeitos com NumPy. Falha (código de saída 1) se qualquer
conferência não passar. O relatório vai para dados/tratados/validacao.txt.
"""
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(RAIZ, 'dados', 'brutos')
TRATADOS = os.path.join(RAIZ, 'dados', 'tratados')

relatorio, falhas = [], []


def conferir(nome, ok, detalhe=''):
    relatorio.append(f'[{"OK" if ok else "FALHA"}] {nome}' + (f': {detalhe}' if detalhe else ''))
    if not ok:
        falhas.append(nome)


def independente():
    """Os oito indicadores, calculados do jeito mais direto possivel, em pandas, com as mesmas regras de
    qualidade do SQL escritas de novo: valor nao positivo sai; valor de um ano fora de 1/4 a 4 vezes a
    media dos outros anos do municipio (reais de 2025) sai."""
    sic = pd.read_csv(os.path.join(BRUTOS, 'siconfi_municipio_ano.csv'))
    mun = pd.read_csv(os.path.join(BRUTOS, 'municipios_sp.csv'))
    est = pd.read_csv(os.path.join(BRUTOS, 'ibge_populacao_estimada.csv')).dropna(subset=['populacao'])
    cen = pd.read_csv(os.path.join(BRUTOS, 'ibge_populacao_censo2022.csv')).dropna(subset=['populacao'])
    pib = pd.read_csv(os.path.join(BRUTOS, 'ibge_pib_corrente_mil_reais.csv')).dropna(subset=['pib_mil_reais'])
    ipca = pd.read_csv(os.path.join(BRUTOS, 'ibge_ipca_indice.csv'))
    ideb = pd.read_csv(os.path.join(BRUTOS, 'ideb_municipio_ano.csv')).dropna()
    sin = pd.read_csv(os.path.join(BRUTOS, 'sinasc_municipio_ano.csv'), dtype={'cod_municipio6': str})

    ipca['ano'] = ipca['mes'] // 100
    medio = ipca.groupby('ano')['indice'].mean()
    fator = (medio[2025] / medio).rename('fator')

    base = pd.concat([
        est[(est.ano >= 2015) & (est.ano <= 2025)][['cod_ibge', 'ano', 'populacao']],
        cen[cen.ano == 2022][['cod_ibge', 'ano', 'populacao']],
    ])
    p24 = est[est.ano == 2024].set_index('cod_ibge').populacao
    p22 = cen.set_index('cod_ibge').populacao
    ambos = p22.index.intersection(p24.index)
    p23 = pd.DataFrame({'cod_ibge': ambos, 'ano': 2023, 'populacao': (p22[ambos] + p24[ambos]) / 2.0})
    pop = pd.concat([base, p23]).drop_duplicates(['cod_ibge', 'ano'])

    def depurar(df, col):
        """Mantem so valores > 0 e dentro de 1/4 a 4 vezes a media dos outros anos."""
        x = df[['cod_ibge', 'ano', col]].dropna()
        x = x[x[col] > 0].copy()
        g = x.groupby('cod_ibge')[col]
        outros = (g.transform('sum') - x[col]) / (g.transform('count') - 1).replace(0, np.nan)
        r = x[col] / outros
        fora = (r < 0.25) | (r > 4)
        return x[~fora]

    s = sic.merge(fator, left_on='ano', right_index=True)
    ic = s[s.entregou_ic == 1].copy()
    ic['rc_liq'] = (ic.rc_bruta - ic.ded_fundeb.fillna(0).abs() - ic.outras_ded.fillna(0).abs()) * ic.fator
    ie = s[s.entregou_ie == 1].copy()
    ie['saude'] = ie.saude_empenhada * ie.fator
    ie['educacao'] = ie.educacao_empenhada * ie.fator
    rc = depurar(ic, 'rc_liq')
    sa = depurar(ie, 'saude')
    ed = depurar(ie, 'educacao')

    saidas = []
    r = rc.merge(pop, on=['cod_ibge', 'ano'])
    r = r[r.populacao > 0]
    saidas.append(pd.DataFrame({'cod_ibge': r.cod_ibge, 'ano': r.ano, 'indicador_id': 'receita_pc',
                                'valor': r.rc_liq / r.populacao}))
    saidas.append(pd.DataFrame({'cod_ibge': rc.cod_ibge, 'ano': rc.ano, 'indicador_id': 'receita_total',
                                'valor': rc.rc_liq / 1e6}))
    d = ic.merge(rc[['cod_ibge', 'ano']], on=['cod_ibge', 'ano'])
    d = d[(d.rc_bruta > 0) & d.transf_correntes.notna()]
    saidas.append(pd.DataFrame({'cod_ibge': d.cod_ibge, 'ano': d.ano, 'indicador_id': 'dependencia_transf',
                                'valor': 100 * d.transf_correntes / d.rc_bruta}))
    for tab, col, ind in ((sa, 'saude', 'saude_pc'), (ed, 'educacao', 'educacao_pc')):
        m = tab.merge(pop, on=['cod_ibge', 'ano'])
        m = m[m.populacao > 0]
        saidas.append(pd.DataFrame({'cod_ibge': m.cod_ibge, 'ano': m.ano, 'indicador_id': ind,
                                    'valor': m[col] / m.populacao}))
    p = pib.merge(fator, left_on='ano', right_index=True).merge(pop, on=['cod_ibge', 'ano'])
    p = p[(p.populacao > 0) & p.ano.between(2015, 2025)]
    saidas.append(pd.DataFrame({'cod_ibge': p.cod_ibge, 'ano': p.ano, 'indicador_id': 'pib_pc',
                                'valor': p.pib_mil_reais * 1000 * p.fator / p.populacao}))
    saidas.append(pd.DataFrame({'cod_ibge': ideb.cod_ibge, 'ano': ideb.ano, 'indicador_id': 'ideb',
                                'valor': ideb.ideb_anos_iniciais_municipal}))
    mun['cod6'] = mun.cod_ibge.astype(str).str[:6]
    n = sin[sin.pre_natal_informado >= 20].merge(mun[['cod_ibge', 'cod6']], left_on='cod_municipio6', right_on='cod6')
    saidas.append(pd.DataFrame({'cod_ibge': n.cod_ibge, 'ano': n.ano, 'indicador_id': 'pre_natal_7mais',
                                'valor': 100 * n.pre_natal_7mais / n.pre_natal_informado}))
    return pd.concat(saidas, ignore_index=True)


def main():
    con = sqlite3.connect(os.path.join(TRATADOS, 'amostra.sqlite'))
    sql = pd.read_sql_query('SELECT cod_ibge, ano, indicador_id, valor FROM fato_indicador', con)
    ref = independente()

    conferir('645 municípios na dimensão', con.execute('SELECT COUNT(*) FROM dim_municipio').fetchone()[0] == 645)
    conferir('chave (município, ano, indicador) sem duplicata', not sql.duplicated(['cod_ibge', 'ano', 'indicador_id']).any())
    meses = pd.read_sql_query('SELECT ano, meses FROM deflator', con)
    conferir('IPCA com 12 meses em cada ano de 2015 a 2025', (meses.meses == 12).all() and len(meses) == 11)

    for ind in sorted(set(sql.indicador_id) | set(ref.indicador_id)):
        a = sql[sql.indicador_id == ind].set_index(['cod_ibge', 'ano']).valor
        b = ref[ref.indicador_id == ind].set_index(['cod_ibge', 'ano']).valor
        m = a.to_frame('sql').join(b.to_frame('pandas'), how='outer')
        so_sql, so_pandas = m.pandas.isna().sum(), m.sql.isna().sum()
        dif = (m.sql - m.pandas).abs().max() if len(m) else 0.0
        conferir(f'{ind}: SQL = pandas', so_sql == 0 and so_pandas == 0 and (dif < 1e-6 or np.isnan(dif)),
                 f'{len(a)} valores, só no SQL {so_sql}, só no pandas {so_pandas}, maior diferença {dif:.2e}')

    # faixas: mediana e quartis refeitos com NumPy
    dim = pd.read_sql_query('SELECT cod_ibge, faixa_porte FROM dim_municipio', con)
    comp = sql.merge(dim, on='cod_ibge')
    tab = pd.read_sql_query('SELECT * FROM ref_faixa', con)
    piores = 0.0
    for (faixa, ano, ind), g in comp.groupby(['faixa_porte', 'ano', 'indicador_id']):
        linha = tab[(tab.faixa_porte == faixa) & (tab.ano == ano) & (tab.indicador_id == ind)]
        esperado = np.percentile(g.valor.values, [25, 50, 75])
        obtido = linha[['p25', 'mediana', 'p75']].values[0]
        piores = max(piores, float(np.max(np.abs(esperado - obtido) / np.maximum(1e-9, np.abs(esperado)))))
        if int(linha.n.values[0]) != len(g):
            conferir(f'n da faixa {faixa} {ano} {ind}', False)
    conferir('quartis por faixa (SQL) = NumPy', piores < 1e-9, f'maior diferença relativa {piores:.2e}')
    conferir('tabela de referência cobre todos os grupos de dados',
             len(tab) == comp.groupby(['faixa_porte', 'ano', 'indicador_id']).ngroups)

    # populacao do Siconfi contra a do IBGE. De 2015 a 2021 as duas partem do Censo 2010 e tem de bater;
    # de 2022 em diante o Siconfi traz outra base (ver sql/20_indicadores.sql): so informamos.
    sic = pd.read_csv(os.path.join(BRUTOS, 'siconfi_municipio_ano.csv'))
    est = pd.read_csv(os.path.join(BRUTOS, 'ibge_populacao_estimada.csv')).dropna(subset=['populacao'])
    j = sic.dropna(subset=['populacao']).merge(est, on=['cod_ibge', 'ano'], suffixes=('_siconfi', '_ibge'))
    j['dif'] = (j.populacao_siconfi / j.populacao_ibge - 1).abs()
    ate21 = j[j.ano <= 2021]
    conferir('população do Siconfi dentro de 5% da do IBGE em 99% dos casos, 2015 a 2021 (mesma base)',
             float(np.quantile(ate21.dif, 0.99)) < 0.05,
             f'{len(ate21)} pares; mediana {100 * ate21.dif.median():.2f}%, p99 {100 * np.quantile(ate21.dif, 0.99):.2f}%')
    depois = j[j.ano >= 2024]
    relatorio.append(f'[info] 2024 e 2025: o Siconfi difere do IBGE em mediana {100 * depois.dif.median():.2f}% e p99 '
                     f'{100 * np.quantile(depois.dif, 0.99):.2f}% (bases diferentes; o painel usa a do IBGE)')

    # a populacao de 2023 fica entre as de 2022 e 2024 em todo municipio
    pop = pd.read_sql_query('SELECT cod_ibge, ano, populacao FROM v_populacao', con).pivot(index='cod_ibge', columns='ano', values='populacao')
    menor = pop[[2022, 2024]].min(axis=1) - 1e-9
    maior = pop[[2022, 2024]].max(axis=1) + 1e-9
    conferir('população de 2023 entre as de 2022 e 2024', bool(((pop[2023] >= menor) & (pop[2023] <= maior)).all()))

    # exclusoes de declaracao: listadas e poucas
    exc = pd.read_sql_query('SELECT * FROM exclusao_declaracao', con)
    conferir('declarações excluídas por inconsistência: menos de 1% das 7.095', len(exc) < 71,
             f'{len(exc)} exclusões em {exc.cod_ibge.nunique()} municípios')

    # plausibilidade
    dep = sql[sql.indicador_id == 'dependencia_transf'].valor
    conferir('dependência de transferências entre 0 e 100%', dep.empty or ((dep >= 0) & (dep <= 100)).all(),
             f'mín {dep.min():.1f} máx {dep.max():.1f}' if len(dep) else 'sem dados')
    pre = sql[sql.indicador_id == 'pre_natal_7mais'].valor
    conferir('pré-natal 7+ entre 0 e 100%', pre.empty or ((pre >= 0) & (pre <= 100)).all())
    ide = sql[sql.indicador_id == 'ideb'].valor
    conferir('Ideb entre 0 e 10', ide.empty or ((ide >= 0) & (ide <= 10)).all())
    for ind in ('receita_pc', 'saude_pc', 'educacao_pc', 'pib_pc', 'receita_total'):
        v = sql[sql.indicador_id == ind].valor
        conferir(f'{ind} positivo', v.empty or (v > 0).all())

    # cobertura de dados (informativa)
    tot = len(dim)
    relatorio.append('')
    relatorio.append('Cobertura: municípios com valor, por indicador e ano (de %d)' % tot)
    pv = sql.pivot_table(index='indicador_id', columns='ano', values='valor', aggfunc='count', fill_value=0)
    relatorio.append(pv.to_string())

    # previsão
    if 'previsao_receita_total' in pd.read_sql_query("SELECT name FROM sqlite_master", con).name.values:
        pr = pd.read_sql_query('SELECT * FROM previsao_receita_total', con)
        ok = ((pr.inferior_95 <= pr.inferior_80) & (pr.inferior_80 <= pr.previsto) &
              (pr.previsto <= pr.superior_80) & (pr.superior_80 <= pr.superior_95)).all()
        conferir('previsão dentro das faixas, 95% contém 80% e o ponto', bool(ok), f'{len(pr)} linhas')
        cob = pd.read_sql_query('SELECT * FROM backtest_cobertura', con)
        relatorio.append('')
        relatorio.append('Cobertura observada das faixas na origem 2022 (calibradas com 2019 a 2021):')
        relatorio.append(cob.to_string(index=False))

    texto = '\n'.join(relatorio)
    with open(os.path.join(TRATADOS, 'validacao.txt'), 'w', encoding='utf-8') as f:
        f.write(texto + '\n')
    print(texto)
    if falhas:
        print('\nFALHARAM:', falhas)
        sys.exit(1)


if __name__ == '__main__':
    main()
