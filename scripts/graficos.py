"""Etapa 5: gráficos em PNG, nas cores de identidade/cores.ts.

    python scripts/graficos.py

Regras da skill dataviz seguidas aqui: uma série destacada em azul e o contexto em cinza; linha de
2 px; marcador de pelo menos 8 px com anel da cor do fundo; grade fina e sem tracejado; legenda
sempre que há duas séries ou mais; rótulo direto só no que conta; texto sempre em tinta, nunca na
cor da série; nenhum eixo duplo. A paleta de duas séries (azul e vermelho) passou no validador da
skill; aqui o segundo tom é o cinza, que é contexto e não identidade.
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

import comum

C = comum.cores()
AZUL, TINTA, CINZA, ZEBRA, BRANCO = C['azul'], C['tinta'], C['cinza'], C['zebra'], C['branco']
CINZA_CLARO = '#CFCDD1'          # um passo entre a zebra e o cinza do texto, para grade e faixa
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans'], 'font.size': 10, 'text.color': TINTA,
    'axes.edgecolor': CINZA_CLARO, 'axes.labelcolor': TINTA, 'xtick.color': TINTA, 'ytick.color': TINTA,
    'axes.facecolor': BRANCO, 'figure.facecolor': BRANCO, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'grid.color': ZEBRA, 'grid.linewidth': 1.0, 'grid.linestyle': '-', 'axes.axisbelow': True,
    'savefig.dpi': 160,
})


def br(x, casas=0):
    s = f'{x:,.{casas}f}'
    return s.replace(',', '#').replace('.', ',').replace('#', '.')


def fmt(casas):
    return FuncFormatter(lambda v, _: br(v, casas))


def ler():
    longo = comum.ler_csv('indicadores_longo.csv')
    dim = {int(r['cod_ibge']): r for r in comum.ler_csv('dim_municipio.csv')}
    ind = {r['indicador_id']: r for r in comum.ler_csv('dim_indicador.csv')}
    ref = {}
    for r in comum.ler_csv('referencia_faixa.csv'):
        ref[(r['faixa_porte'], int(r['ano']), r['indicador_id'])] = {k: float(r[k]) for k in ('p25', 'mediana', 'p75')} | {'n': int(r['n'])}
    valor = {}
    for r in longo:
        valor[(int(r['cod_ibge']), int(r['ano']), r['indicador_id'])] = float(r['valor'])
    return valor, dim, ind, ref


def salvar(fig, nome):
    os.makedirs(comum.GRAFICOS, exist_ok=True)
    fig.savefig(os.path.join(comum.GRAFICOS, nome), bbox_inches='tight')
    plt.close(fig)
    print('gravado', nome)


def serie(valor, cod, ind, anos):
    return [valor.get((cod, a, ind), np.nan) for a in anos]


def painel(valor, dim, ind, ref, cod):
    faixa = dim[cod]['faixa_porte']
    fig, eixos = plt.subplots(2, 4, figsize=(15, 7.2))
    for ax, i in zip(eixos.flat, comum.INDICADORES_PAINEL):
        anos = [a for a in comum.ANOS if (faixa, a, i) in ref]
        y = np.array(serie(valor, cod, i, anos))
        med = np.array([ref[(faixa, a, i)]['mediana'] for a in anos])
        q1 = np.array([ref[(faixa, a, i)]['p25'] for a in anos])
        q3 = np.array([ref[(faixa, a, i)]['p75'] for a in anos])
        ax.fill_between(anos, q1, q3, color=CINZA, alpha=0.12, linewidth=0)
        ax.plot(anos, med, color=CINZA, lw=2, solid_capstyle='round')
        ok = ~np.isnan(y)
        ax.plot(np.array(anos)[ok], y[ok], color=AZUL, lw=2, marker='o', ms=6, mec=BRANCO, mew=1.5,
                solid_capstyle='round')
        casas = int(ind[i]['casas'])
        ax.yaxis.set_major_formatter(fmt(casas))
        ax.set_title(ind[i]['nome'], fontsize=10, loc='left', fontweight='bold')
        ax.set_xticks([2015, 2020, 2025] if max(anos) >= 2025 else [2015, 2019, 2023])
        ax.tick_params(length=0)
        ax.text(0, 1.0, '', transform=ax.transAxes)
        unidade = ind[i]['unidade'].replace('a preços de 2025', 'de 2025')
        ax.text(0, -0.2, unidade, transform=ax.transAxes, fontsize=8, color=CINZA)
    leg = eixos.flat[7]
    leg.axis('off')
    leg.plot([], [], color=AZUL, lw=2, marker='o', ms=6, mec=BRANCO, label=dim[cod]['municipio'])
    leg.plot([], [], color=CINZA, lw=2, label='Mediana dos municípios da faixa')
    leg.fill_between([], [], [], color=CINZA, alpha=0.12, label='Do 1º ao 3º quartil da faixa')
    leg.legend(loc='upper left', frameon=False, fontsize=10)
    leg.text(0, 0.28, f'Faixa de porte: {faixa[3:]} habitantes\n(Censo 2022)\n{ref[(faixa, 2024, "receita_pc")]["n"]} municípios na faixa',
             transform=leg.transAxes, fontsize=9, color=TINTA, va='top')
    fig.suptitle(f'Município de exemplo comparado com os municípios da sua faixa de porte, 2015 a 2025',
                 x=0.01, ha='left', fontsize=13, fontweight='bold')
    fig.text(0.01, 0.005, 'Fontes: Siconfi/Tesouro, IBGE, INEP, DataSUS. Valores em reais de 2025 (IPCA). Município sorteado com semente fixa entre os de série completa.',
             fontsize=8, color=CINZA)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95), h_pad=3)
    salvar(fig, '01-painel-municipio.png')


def faixa_dispersao(valor, dim, ind, ref, cod):
    faixa = dim[cod]['faixa_porte']
    ano = 2025
    pares = [('receita_pc', ano), ('saude_pc', ano), ('educacao_pc', ano)]
    fig, eixos = plt.subplots(1, 3, figsize=(13, 3.8))
    rng = np.random.default_rng(comum.SEMENTE)
    for ax, (i, a) in zip(eixos, pares):
        outros = [valor[(c, a, i)] for c in dim if dim[c]['faixa_porte'] == faixa and (c, a, i) in valor and c != cod]
        y = rng.uniform(-0.35, 0.35, len(outros))
        ax.scatter(outros, y, s=22, color=CINZA, alpha=0.45, linewidths=0)
        r = ref[(faixa, a, i)]
        ax.axvline(r['mediana'], color=TINTA, lw=1.5)
        ax.text(r['mediana'], 0.66, ' mediana', ha='left', fontsize=8.5, color=TINTA)
        v = valor.get((cod, a, i))
        if v is not None:
            ax.scatter([v], [0], s=110, color=AZUL, edgecolors=BRANCO, linewidths=2, zorder=5)
            ax.annotate(dim[cod]['municipio'], (v, 0), xytext=(0, 26), textcoords='offset points', ha='center',
                        fontsize=9, color=TINTA, bbox=dict(boxstyle='round,pad=0.25', fc=BRANCO, ec='none', alpha=0.9),
                        arrowprops=dict(arrowstyle='-', color=CINZA, lw=1))
        ax.set_ylim(-0.8, 0.8)
        ax.set_yticks([])
        ax.xaxis.set_major_formatter(fmt(0))
        ax.set_title(ind[i]['nome'] + f' ({a})', fontsize=10, loc='left', fontweight='bold')
        ax.grid(axis='y', visible=False)
        ax.spines['left'].set_visible(False)
        ax.tick_params(length=0)
        ax.set_xlabel('R$ por habitante, a preços de 2025')
    fig.suptitle(f'Cada ponto cinza é um município da faixa {faixa[3:]} habitantes; o azul é o município de exemplo',
                 x=0.01, ha='left', fontsize=12, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    salvar(fig, '02-municipio-na-faixa.png')


def previsao(valor, dim, ind, cod):
    prev = {(int(r['cod_ibge']), int(r['ano'])): r for r in comum.ler_csv('previsao_receita_total.csv')}
    anos = comum.ANOS
    y = [valor.get((cod, a, 'receita_total'), np.nan) for a in anos]
    fa = [2026, 2027, 2028]
    f = [prev[(cod, a)] for a in fa]
    x_prev = [2025] + fa
    ponto = [y[-1]] + [float(r['previsto']) for r in f]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for nivel, alpha in (('95', 0.10), ('80', 0.20)):
        lo = [y[-1]] + [float(r[f'inferior_{nivel}']) for r in f]
        hi = [y[-1]] + [float(r[f'superior_{nivel}']) for r in f]
        ax.fill_between(x_prev, lo, hi, color=AZUL, alpha=alpha, linewidth=0)
    ax.plot(anos, y, color=AZUL, lw=2, marker='o', ms=6, mec=BRANCO, mew=1.5)
    ax.plot(x_prev, ponto, color=AZUL, lw=2, ls=(0, (4, 3)), marker='o', ms=6, mfc=BRANCO, mec=AZUL, mew=1.5)
    ax.yaxis.set_major_formatter(fmt(0))
    ax.set_xticks(anos + fa)
    ax.tick_params(length=0)
    ax.set_ylabel('R$ milhões, a preços de 2025')
    ax.annotate('observado', (anos[1], y[1]), xytext=(0, 12), textcoords='offset points', ha='center', fontsize=9)
    ax.annotate(f'previsto 2028: R$ {br(ponto[-1], 0)} mi', (2028, ponto[-1]), xytext=(-8, 14), textcoords='offset points',
                ha='right', fontsize=9)
    ax.plot([], [], color=AZUL, lw=2, label='Observado')
    ax.plot([], [], color=AZUL, lw=2, ls=(0, (4, 3)), label='Previsto')
    ax.fill_between([], [], [], color=AZUL, alpha=0.20, label='Faixa de 80%')
    ax.fill_between([], [], [], color=AZUL, alpha=0.10, label='Faixa de 95%')
    ax.legend(loc='lower left', frameon=False, fontsize=9, ncol=2)
    ax.set_title(f'Receita corrente de {dim[cod]["municipio"]}: observado até 2025 e previsão para 2026 a 2028',
                 loc='left', fontsize=11, fontweight='bold')
    fig.text(0.01, -0.04,
             f'Método: {f[0]["metodo"]} sobre o logaritmo da série. A faixa vem dos erros que o método cometeu\n'
             'ao prever o passado de todos os municípios do mesmo grupo de porte (scripts/modelo.py).',
             fontsize=8, color=CINZA)
    salvar(fig, '03-previsao.png')


def backtest():
    metodos = comum.ler_csv('backtest_metodos.csv')
    cob = comum.ler_csv('backtest_cobertura.csv')
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.4))
    nomes = {'ingenuo': 'Repetir o último valor', 'tendencia3': 'Tendência dos 3 últimos anos',
             'tendencia5': 'Reta dos 5 últimos anos'}
    ordem = ['ingenuo', 'tendencia3', 'tendencia5']
    hs = sorted({int(r['horizonte']) for r in metodos})
    larg = 0.24
    escolhido = next(r['metodo'] for r in metodos if r['escolhido'] == '1')
    for k, m in enumerate(ordem):
        v = [float(next(r['erro_medio_abs_pct'] for r in metodos if r['metodo'] == m and int(r['horizonte']) == h)) for h in hs]
        x = np.arange(len(hs)) + (k - 1) * (larg + 0.03)
        a.bar(x, v, width=larg, color=AZUL if m == escolhido else CINZA, alpha=1 if m == escolhido else 0.55)
        for xi, vi in zip(x, v):
            a.text(xi, vi + 0.15, br(vi, 1), ha='center', fontsize=8)
    a.set_xticks(np.arange(len(hs)))
    a.set_xticklabels([f'{h} ano{"s" if h > 1 else ""} à frente' for h in hs])
    a.yaxis.set_major_formatter(fmt(1))
    a.set_ylabel('Erro médio absoluto, % do valor')
    a.set_title('Quanto cada método errou ao prever o passado', loc='left', fontsize=11, fontweight='bold')
    a.grid(axis='x', visible=False)
    a.tick_params(length=0)
    from matplotlib.patches import Patch
    a.legend(handles=[Patch(facecolor=AZUL if m == escolhido else CINZA, alpha=1 if m == escolhido else 0.55,
                            label=nomes[m] + (' (escolhido)' if m == escolhido else '')) for m in ordem],
             frameon=False, fontsize=8.5, loc='upper left')

    origens = sorted({int(r['origem_fora']) for r in cob})
    for nv, cor in ((80, AZUL), (95, TINTA)):
        sem, com = [], []
        for T0 in origens:
            ll = [r for r in cob if int(r['origem_fora']) == T0 and int(r['nivel']) == nv]
            n = sum(int(r['n_teste']) for r in ll)
            sem.append(sum(float(r['cobertura_sem_ajuste']) * int(r['n_teste']) for r in ll) / n)
            com.append(sum(float(r['cobertura_com_ajuste']) * int(r['n_teste']) for r in ll) / n)
        b.scatter(origens, sem, s=70, facecolors=BRANCO, edgecolors=cor, linewidths=2, zorder=3)
        b.scatter(origens, com, s=70, color=cor, edgecolors=BRANCO, linewidths=1.5, zorder=4, label=f'Faixa de {nv}%, ajustada')
        b.axhline(nv, color=cor, lw=1, alpha=0.5)
        b.text(origens[-1] + 0.45, nv, f'{nv}%', va='center', fontsize=8.5)
    b.set_xticks(origens)
    b.set_xticklabels([f'{o} fora' for o in origens])
    b.set_xlim(origens[0] - 0.5, origens[-1] + 0.9)
    b.set_ylim(40, 102)
    b.set_ylabel('% dos valores reais dentro da faixa')
    b.set_title('A faixa cobre o que promete? Teste com uma origem de fora', loc='left', fontsize=11, fontweight='bold')
    from matplotlib.lines import Line2D
    b.legend(handles=[Line2D([], [], marker='o', ls='', mfc=AZUL, mec=BRANCO, ms=8, label='Faixa de 80%, depois do ajuste'),
                      Line2D([], [], marker='o', ls='', mfc=TINTA, mec=BRANCO, ms=8, label='Faixa de 95%, depois do ajuste'),
                      Line2D([], [], marker='o', ls='', mfc=BRANCO, mec=CINZA, ms=8, label='Antes do ajuste (círculo vazado)')],
             frameon=False, fontsize=8.5, loc='lower left')
    b.grid(axis='x', visible=False)
    b.tick_params(length=0)
    fig.text(0.01, -0.03, 'Cada ponto: a faixa calibrada com as outras três origens (anos em que a previsão partiu) e conferida na que ficou de fora. '
             'Linhas finas: cobertura prometida.', fontsize=8, color=CINZA)
    salvar(fig, '04-teste-do-modelo.png')


def main():
    valor, dim, ind, ref = ler()
    cod, n = comum.municipio_de_exemplo()
    print('município de exemplo:', cod, dim[cod]['municipio'], '(sorteado entre', n, ')')
    painel(valor, dim, ind, ref, cod)
    faixa_dispersao(valor, dim, ind, ref, cod)
    if os.path.exists(os.path.join(comum.TRATADOS, 'previsao_receita_total.csv')):
        previsao(valor, dim, ind, cod)
        backtest()


if __name__ == '__main__':
    main()
