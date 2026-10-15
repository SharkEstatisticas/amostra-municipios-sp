"""Etapa 3: previsão da receita corrente real de cada município, com a incerteza à vista.

    python scripts/modelo.py

Série: receita corrente líquida de deduções, em R$ milhões de 2025 (indicador "receita_total"),
anual, 2015 a 2025. Trabalha no logaritmo, para que o erro seja proporcional ao tamanho do município.

Três métodos simples, todos tirando só da própria série do município:
  ingenuo     : o último valor se repete;
  tendencia3  : o último valor mais h vezes a média das 3 últimas variações anuais do logaritmo;
  tendencia5  : reta ajustada por mínimos quadrados aos 5 últimos pontos, estendida h anos.

Como escolher e quanto confiar (a parte que importa):
  1. Teste retrospectivo ("backtest"): para cada origem T de 2019 a 2022 e cada horizonte h de 1 a 3
     com T + h <= 2025, o método prevê usando só dados até T e o erro é medido contra o que veio.
  2. O método com menor erro médio absoluto (em log) é o escolhido.
  3. A faixa de incerteza vem dos erros de verdade: quantis dos erros do teste retrospectivo, por
     horizonte e por grupo de porte. Não é fórmula de livro-texto com erro normal.
  4. A receita dos municípios se move junta (inflação, ICMS, transferências da União): o erro de um
     ano é em boa parte comum a todos. Por isso os 4 anos de origem são 4 "choques" quase independentes,
     e a faixa calibrada em alguns deles não cobre o que prometeu em outro. O teste que mostra isso é o
     "deixa uma origem de fora": calibra com 3 origens, confere na quarta, e repete para as quatro.
  5. A faixa é alargada por um fator (o menor, de 1,00 a 3,00, com que a cobertura do teste do passo 4
     chega ao nível prometido). Com 4 origens o ajuste é grosseiro, e o texto de quem usa a previsão diz
     isso. A cobertura antes e depois do ajuste vai em backtest_cobertura.csv.
"""
import csv
import math
import os
import sqlite3
from collections import defaultdict

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRATADOS = os.path.join(RAIZ, 'dados', 'tratados')
ANOS = list(range(2015, 2026))
ULTIMO = 2025
HORIZONTES = (1, 2, 3)
ORIGENS = (2019, 2020, 2021, 2022)
NIVEIS = {'80': (0.10, 0.90), '95': (0.025, 0.975)}
ESCALAS = [round(1.0 + 0.05 * k, 2) for k in range(0, 41)]   # 1,00 a 3,00


def grupo_de_porte(pop):
    """Três grupos, para que cada um tenha erros suficientes por horizonte."""
    if pop <= 10000:
        return 'A. Até 10 mil'
    if pop <= 50000:
        return 'B. De 10 a 50 mil'
    return 'C. Mais de 50 mil'


def prever(y, origem_idx, h, metodo):
    """y: vetor em log; origem_idx: posição do último ponto conhecido; devolve o log previsto."""
    ult = y[origem_idx]
    if metodo == 'ingenuo':
        return ult
    if metodo == 'tendencia3':
        janela = y[origem_idx - 3: origem_idx + 1]
        return ult + h * float(np.mean(np.diff(janela)))
    if metodo == 'tendencia5':
        janela = y[origem_idx - 4: origem_idx + 1]
        x = np.arange(5)
        b, a = np.polyfit(x, janela, 1)
        return a + b * (4 + h)
    raise ValueError(metodo)


METODOS = ('ingenuo', 'tendencia3', 'tendencia5')


def ler():
    receita, grupo, nome = {}, {}, {}
    with open(os.path.join(TRATADOS, 'indicadores_longo.csv'), encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            if r['indicador_id'] != 'receita_total':
                continue
            cod = int(r['cod_ibge'])
            receita.setdefault(cod, {})[int(r['ano'])] = float(r['valor'])
            nome[cod] = r['municipio']
    with open(os.path.join(TRATADOS, 'dim_municipio.csv'), encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            grupo[int(r['cod_ibge'])] = grupo_de_porte(int(r['populacao_censo_2022']))
    return receita, grupo, nome


def main():
    receita, grupo, nome = ler()
    completos = [c for c, s in receita.items() if all(a in s and s[a] > 0 for a in ANOS)]
    print(len(receita), 'municípios com algum valor;', len(completos), 'com a série 2015 a 2025 completa')
    serie = {c: np.log([receita[c][a] for a in ANOS]) for c in completos}
    idx = {a: i for i, a in enumerate(ANOS)}

    # 1. erros do teste retrospectivo: (metodo, h, origem, grupo) -> lista de erros com sinal (real − previsto, em log)
    erros = defaultdict(list)
    for c, y in serie.items():
        for T in ORIGENS:
            for h in HORIZONTES:
                if T + h > ULTIMO:
                    continue
                real = y[idx[T + h]]
                for m in METODOS:
                    erros[(m, h, T, grupo[c])].append(real - prever(y, idx[T], h, m))

    # 2. erro por método e horizonte; escolha do método
    linhas_metodo, pooled = [], defaultdict(list)
    for m in METODOS:
        for h in HORIZONTES:
            e = [x for (mm, hh, T, g), v in erros.items() if mm == m and hh == h for x in v]
            pooled[m] += e
            linhas_metodo.append(dict(metodo=m, horizonte=h, n=len(e), erro_medio_abs_pct=100 * float(np.mean(np.abs(e))),
                                      erro_mediano_abs_pct=100 * float(np.median(np.abs(e))),
                                      vies_pct=100 * float(np.mean(e))))
    escolhido = min(METODOS, key=lambda m: float(np.mean(np.abs(pooled[m]))))
    for l in linhas_metodo:
        l['escolhido'] = int(l['metodo'] == escolhido)
    print('método escolhido:', escolhido)
    for l in linhas_metodo:
        print('  ', l['metodo'], 'h=%d' % l['horizonte'], 'n=%d' % l['n'], 'erro médio abs %.1f%%' % l['erro_medio_abs_pct'],
              'viés %.1f%%' % l['vies_pct'])

    grupos = sorted(set(grupo.values()))

    def quantis(origens, h, g, nv):
        e = [x for T in origens for x in erros[(escolhido, h, T, g)]]
        lo, hi = (float(np.quantile(e, q)) for q in NIVEIS[nv])
        return lo, hi

    def faixa(lo, hi, escala):
        centro, meia = (lo + hi) / 2, (hi - lo) / 2
        return centro - escala * meia, centro + escala * meia

    # 3. "deixa uma origem de fora": calibra com as outras origens e confere na que ficou de fora
    def cobertura(nv, escala):
        """Devolve {(T0, g, h): (acertos, n)} para o nível e a escala dados."""
        r = {}
        for T0 in ORIGENS:
            for g in grupos:
                for h in HORIZONTES:
                    if T0 + h > ULTIMO:
                        continue
                    cal = [T for T in ORIGENS if T != T0 and T + h <= ULTIMO]
                    lo, hi = faixa(*quantis(cal, h, g, nv), escala)
                    e = erros[(escolhido, h, T0, g)]
                    r[(T0, g, h)] = (sum(lo <= x <= hi for x in e), len(e))
        return r

    escala_por_nivel = {}
    for nv in NIVEIS:
        alvo = int(nv) / 100
        achada = ESCALAS[-1]
        for s in ESCALAS:
            c = cobertura(nv, s)
            if sum(a for a, _ in c.values()) / sum(n for _, n in c.values()) >= alvo:
                achada = s
                break
        escala_por_nivel[nv] = achada
    print('fator de alargamento da faixa por nível:', escala_por_nivel)

    cobertura_linhas = []
    for nv in NIVEIS:
        antes, depois = cobertura(nv, 1.0), cobertura(nv, escala_por_nivel[nv])
        for (T0, g, h), (a0, n) in antes.items():
            a1, _ = depois[(T0, g, h)]
            cobertura_linhas.append(dict(origem_fora=T0, grupo=g, horizonte=h, nivel=int(nv), n_teste=n,
                                         cobertura_sem_ajuste=100 * a0 / n, cobertura_com_ajuste=100 * a1 / n))
    for nv in NIVEIS:
        a0 = sum(l['cobertura_sem_ajuste'] * l['n_teste'] for l in cobertura_linhas if l['nivel'] == int(nv))
        a1 = sum(l['cobertura_com_ajuste'] * l['n_teste'] for l in cobertura_linhas if l['nivel'] == int(nv))
        n = sum(l['n_teste'] for l in cobertura_linhas if l['nivel'] == int(nv))
        print(f'  nível {nv}%: cobertura com uma origem de fora, sem ajuste {a0 / n:.0f}%, com ajuste {a1 / n:.0f}% (n={n})')
        for T0 in ORIGENS:
            ll = [l for l in cobertura_linhas if l['nivel'] == int(nv) and l['origem_fora'] == T0]
            nn = sum(l['n_teste'] for l in ll)
            print(f'    origem {T0} fora: sem ajuste {sum(l["cobertura_sem_ajuste"] * l["n_teste"] for l in ll) / nn:.0f}%,'
                  f' com ajuste {sum(l["cobertura_com_ajuste"] * l["n_teste"] for l in ll) / nn:.0f}%')

    # 4. quantis finais (todas as origens) com o ajuste, e previsão de 2026 a 2028
    parametros, previsoes, final = [], [], {}
    for g in grupos:
        for h in HORIZONTES:
            for nv in NIVEIS:
                lo, hi = quantis([T for T in ORIGENS if T + h <= ULTIMO], h, g, nv)
                lo2, hi2 = faixa(lo, hi, escala_por_nivel[nv])
                final[(g, h, nv)] = (lo2, hi2)
                n = sum(len(erros[(escolhido, h, T, g)]) for T in ORIGENS if T + h <= ULTIMO)
                parametros.append(dict(grupo=g, horizonte=h, nivel=int(nv), n=n, q_inferior_bruto=lo, q_superior_bruto=hi,
                                       escala=escala_por_nivel[nv], q_inferior=lo2, q_superior=hi2))

    sem_previsao = 0
    for c, s in receita.items():
        ultimos = [s.get(a) for a in range(ULTIMO - 4, ULTIMO + 1)]
        if any(v is None or v <= 0 for v in ultimos):
            sem_previsao += 1
            continue
        y = np.log([s[a] if (a in s and s[a] > 0) else float('nan') for a in ANOS])
        for h in HORIZONTES:
            centro = prever(y, idx[ULTIMO], h, escolhido)
            linha = dict(cod_ibge=c, municipio=nome[c], grupo_porte=grupo[c], ano=ULTIMO + h, metodo=escolhido,
                         previsto=math.exp(centro))
            for nv in NIVEIS:
                lo, hi = final[(grupo[c], h, nv)]
                linha[f'inferior_{nv}'] = math.exp(centro + lo)
                linha[f'superior_{nv}'] = math.exp(centro + hi)
            previsoes.append(linha)
    print(len({p['cod_ibge'] for p in previsoes}), 'municípios com previsão;', sem_previsao, 'sem os 5 últimos anos válidos')

    def gravar(arquivo, linhas):
        with open(os.path.join(TRATADOS, arquivo), 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            w.writeheader()
            w.writerows(linhas)

    gravar('backtest_metodos.csv', linhas_metodo)
    gravar('backtest_cobertura.csv', cobertura_linhas)
    gravar('modelo_quantis.csv', parametros)
    gravar('previsao_receita_total.csv', previsoes)

    # os mesmos resultados dentro da base, para as consultas SQL
    con = sqlite3.connect(os.path.join(TRATADOS, 'amostra.sqlite'))
    for tabela, linhas in (('previsao_receita_total', previsoes), ('backtest_metodos', linhas_metodo),
                           ('backtest_cobertura', cobertura_linhas), ('modelo_quantis', parametros)):
        con.execute(f'DROP TABLE IF EXISTS {tabela}')
        cols = list(linhas[0].keys())
        con.execute(f'CREATE TABLE {tabela} ({", ".join(cols)})')
        con.executemany(f'INSERT INTO {tabela} VALUES ({",".join("?" * len(cols))})', [[l[c] for c in cols] for l in linhas])
    con.commit()
    con.close()


if __name__ == '__main__':
    main()
