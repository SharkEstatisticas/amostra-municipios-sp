"""Etapa 8: números de conferência para quem monta o painel no Power BI (powerbi/conferencia.md).

    python scripts/gerar_conferencia.py

Lê o SQLite e escreve, para três municípios de faixas diferentes, o que cada medida DAX da
especificação tem de devolver. Os três são sorteados com semente fixa, um por faixa de porte
(pequeno, médio, grande), entre os que têm todos os indicadores em 2024.
"""
import os
import random
import sqlite3

import comum

SAIDA = os.path.join(comum.RAIZ, 'powerbi', 'conferencia.md')


def main():
    con = sqlite3.connect(os.path.join(comum.TRATADOS, 'amostra.sqlite'))
    inds = [r[0] for r in con.execute("SELECT indicador_id FROM dim_indicador WHERE indicador_id NOT IN ('receita_total') ORDER BY ordem")]
    completos = {}
    for cod, faixa in con.execute('SELECT cod_ibge, faixa_porte FROM dim_municipio'):
        n = con.execute("SELECT COUNT(DISTINCT indicador_id) FROM fato_indicador WHERE cod_ibge=? AND ano=2023 AND indicador_id IN (%s)"
                        % ','.join('?' * len(inds)), [cod] + inds).fetchone()[0]
        if n == len(inds):          # 2023 é o último ano em que os sete indicadores coexistem (PIB e Ideb)
            completos.setdefault(faixa, []).append(cod)
    rng = random.Random(comum.SEMENTE)
    alvo = [rng.choice(sorted(completos[f])) for f in ('2. De 5 a 10 mil', '4. De 20 a 50 mil', '6. De 100 a 500 mil')]
    linhas = ['# Números de conferência do painel de Power BI', '',
              'Gerado por `scripts/gerar_conferencia.py` a partir de `dados/tratados/amostra.sqlite`. '
              'Para cada município abaixo, escolha-o na segmentação, selecione o indicador e o ano e compare o que as medidas devolvem '
              'com as colunas desta tabela. Município e ano de cada linha: ano 2023, o último em que os sete indicadores por município coexistem.', '']
    for cod in alvo:
        nome, faixa, pop = con.execute('SELECT municipio, faixa_porte, populacao_censo_2022 FROM dim_municipio WHERE cod_ibge=?', (cod,)).fetchone()
        linhas += [f'## {nome}', '', f'Faixa de porte: {faixa}. População (Censo 2022): {pop:,}'.replace(',', '.'), '',
                   '| Indicador | `[Valor]` 2023 | `[Mediana da faixa]` | `[1º quartil da faixa]` | `[3º quartil da faixa]` | `[Diferença para a mediana]` | `[Posição na faixa]` | Municípios na faixa com dado |',
                   '|---|---|---|---|---|---|---|---|']
        for i in inds:
            v, med, q1, q3, n = con.execute(
                'SELECT f.valor, r.mediana, r.p25, r.p75, r.n FROM fato_indicador f JOIN dim_municipio d ON d.cod_ibge=f.cod_ibge '
                'JOIN ref_faixa r ON r.faixa_porte=d.faixa_porte AND r.ano=f.ano AND r.indicador_id=f.indicador_id '
                'WHERE f.cod_ibge=? AND f.ano=2023 AND f.indicador_id=?', (cod, i)).fetchone()
            pos = con.execute('SELECT posicao_na_faixa FROM v_posicao WHERE cod_ibge=? AND ano=2023 AND indicador_id=?', (cod, i)).fetchone()[0]
            linhas.append(f'| {i} | {v:.4f} | {med:.4f} | {q1:.4f} | {q3:.4f} | {100 * (v / med - 1):+.2f}% | {pos / 100:.4f} | {n} |'.replace('.', ','))
        p = con.execute('SELECT ano, previsto, inferior_80, superior_80 FROM previsao_receita_total WHERE cod_ibge=? ORDER BY ano', (cod,)).fetchall()
        if p:
            linhas += ['', 'Previsão da receita (R$ milhões de 2025):', '', '| Ano | `[Receita prevista]` | `[Limite inferior 80%]` | `[Limite superior 80%]` |', '|---|---|---|---|']
            for a, pr, lo, hi in p:
                linhas.append(f'| {a} | {pr:.3f} | {lo:.3f} | {hi:.3f} |'.replace('.', ','))
        linhas.append('')
    linhas += ['Os números usam vírgula decimal. A posição está em fração (0,5 = 50%), como a medida `[Posição na faixa]` a devolve antes do formato de porcentagem.']
    with open(SAIDA, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')
    print('gravado', SAIDA)


if __name__ == '__main__':
    main()
