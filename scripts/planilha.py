"""Etapa 6: a planilha Excel (tabelas, fórmulas e gráficos) em excel/amostra-municipios-sp.xlsx.

    python scripts/planilha.py

O que alguém de fora faz: abre, escolhe um município na célula amarela da aba "Painel" e tudo se
recalcula (aba "Tabela do município", gráficos do "Painel", aba "Previsão"). Nada é colado como valor
nas abas de leitura: cada número é fórmula sobre as abas de dados ("Dados", "Referência", "Previsões",
"Municípios"), que são os CSV de dados/tratados/.

xlsxwriter não calcula fórmulas; ele grava a fórmula e o valor que o Excel mostra antes de recalcular
(o valor em cache, calculado aqui em Python, o mesmo que a fórmula dá). scripts/verificar_planilha.py
recalcula as fórmulas com um motor independente e compara com esse cache.
"""
import os

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

import comum

C = comum.cores()
AZUL, TINTA, CINZA, ZEBRA = C['azul'], C['tinta'], C['cinza'], C['zebra']
CINZA_CLARO = '#CFCDD1'
SAIDA = os.path.join(comum.EXCEL, 'amostra-municipios-sp.xlsx')
ANOS = comum.ANOS
NA = 'n.d.'
ORDEM_DADOS = ['receita_pc', 'dependencia_transf', 'saude_pc', 'educacao_pc', 'pib_pc', 'ideb', 'pre_natal_7mais', 'receita_total']
COL_DADOS = {ind: 5 + k for k, ind in enumerate(ORDEM_DADOS)}   # F..M (índice 0: A)


def carregar():
    dim_m = comum.ler_csv('dim_municipio.csv')
    dim_i = comum.ler_csv('dim_indicador.csv')
    valor = {}
    for r in comum.ler_csv('indicadores_longo.csv'):
        valor[(int(r['cod_ibge']), int(r['ano']), r['indicador_id'])] = float(r['valor'])
    ref = {}
    for r in comum.ler_csv('referencia_faixa.csv'):
        ref[(r['faixa_porte'], int(r['ano']), r['indicador_id'])] = r
    prev = {}
    for r in comum.ler_csv('previsao_receita_total.csv'):
        prev[(int(r['cod_ibge']), int(r['ano']))] = r
    bt_m = comum.ler_csv('backtest_metodos.csv')
    bt_c = comum.ler_csv('backtest_cobertura.csv')
    return dim_m, dim_i, valor, ref, prev, bt_m, bt_c


def main():
    dim_m, dim_i, valor, ref, prev, bt_m, bt_c = carregar()
    cod_ex, _ = comum.municipio_de_exemplo()
    info = {int(r['cod_ibge']): r for r in dim_m}
    ind = {r['indicador_id']: r for r in dim_i}
    nome_ex = info[cod_ex]['municipio']
    faixa_ex = info[cod_ex]['faixa_porte']

    os.makedirs(comum.EXCEL, exist_ok=True)
    wb = xlsxwriter.Workbook(SAIDA, {'default_format_properties': {'font_name': 'Arial', 'font_size': 10}})
    wb.set_properties({'title': 'Painel de indicadores dos municípios de SP (amostra)', 'subject': 'Entregável de amostra, dado público',
                       'author': 'Shark Estatística', 'comments': 'Feito com dado público e sem Cliente. A Revisão técnica por estatístico registrado no CONRE ainda não está registrada para esta amostra.'})

    def fmt(**kw):
        base = {'font_name': 'Arial', 'font_size': 10, 'valign': 'top'}
        base.update(kw)
        return wb.add_format(base)

    f_titulo = fmt(bold=True, font_size=16, font_color=TINTA)
    f_sub = fmt(font_color=CINZA, text_wrap=True)
    f_h = fmt(bold=True, bg_color=ZEBRA, bottom=1, bottom_color=CINZA_CLARO, text_wrap=True, valign='vcenter')
    f_txt = fmt(text_wrap=True)
    f_neg = fmt(bold=True)
    f_in = fmt(bold=True, font_color='#0000FF', bg_color='#FFF2CC', border=1, border_color=CINZA)
    f_n0 = fmt(num_format='#,##0')
    f_n1 = fmt(num_format='#,##0.0')
    f_pct = fmt(num_format='+0.0%;-0.0%;0.0%')
    f_pct0 = fmt(num_format='0%')
    f_cinza = fmt(font_color=CINZA, font_size=9, text_wrap=True)
    f_apoio = fmt(font_color=CINZA, font_size=9, num_format='#,##0.0')
    f_ano = fmt(bold=True, bg_color=ZEBRA, align='center', num_format='0', bottom=1, bottom_color=CINZA_CLARO)
    f_aviso = fmt(text_wrap=True, bg_color=ZEBRA, border=1, border_color=CINZA_CLARO)

    def fnum(i):
        return f_n1 if int(ind[i]['casas']) >= 1 else f_n0

    def v(cod, ano, i):
        return valor.get((cod, ano, i))

    # ---------------------------------------------------------------- abas, na ordem de leitura
    ws_leia = wb.add_worksheet('Leia-me')
    ws_pn = wb.add_worksheet('Painel')
    ws_tb = wb.add_worksheet('Tabela do município')
    ws_pr = wb.add_worksheet('Previsão')
    ws_in = wb.add_worksheet('Indicadores')
    ws_fo = wb.add_worksheet('Fontes e licenças')
    ws_da = wb.add_worksheet('Dados')
    ws_re = wb.add_worksheet('Referência')
    ws_pv = wb.add_worksheet('Previsões')
    ws_mu = wb.add_worksheet('Municípios')
    for w in (ws_leia, ws_pn, ws_tb, ws_pr, ws_in, ws_fo):
        w.hide_gridlines(2)
        w.set_default_row(15)

    # ---------------------------------------------------------------- Municípios
    ws_mu.write_row(0, 0, ['Código IBGE', 'Município', 'Faixa de porte', 'Região geográfica imediata', 'População (Censo 2022)',
                           'Grupo de porte do modelo'], f_h)
    from modelo import grupo_de_porte
    ordem_m = sorted(dim_m, key=lambda r: r['municipio'])      # por nome, para a lista suspensa
    for k, r in enumerate(ordem_m, start=1):
        ws_mu.write_number(k, 0, int(r['cod_ibge']))
        ws_mu.write_string(k, 1, r['municipio'])
        ws_mu.write_string(k, 2, r['faixa_porte'])
        ws_mu.write_string(k, 3, r['regiao_imediata'])
        ws_mu.write_number(k, 4, int(r['populacao_censo_2022']), f_n0)
        ws_mu.write_string(k, 5, grupo_de_porte(int(r['populacao_censo_2022'])))
    n_mu = len(ordem_m)
    ws_mu.set_column(0, 0, 12); ws_mu.set_column(1, 1, 30); ws_mu.set_column(2, 3, 28); ws_mu.set_column(4, 5, 22)
    ws_mu.freeze_panes(1, 0)
    R_MU = lambda c: f"'Municípios'!${c}$2:${c}${n_mu + 1}"

    # ---------------------------------------------------------------- Dados (uma linha por município e ano)
    cab = ['Chave', 'Código IBGE', 'Município', 'Ano', 'Faixa de porte'] + [ind[i]['nome'] for i in ORDEM_DADOS]
    ws_da.write_row(0, 0, cab, f_h)
    linha = 1
    ordem_cod = [int(r['cod_ibge']) for r in dim_m]
    for cod in ordem_cod:
        for a in ANOS:
            ws_da.write_string(linha, 0, f'{cod}|{a}')
            ws_da.write_number(linha, 1, cod)
            ws_da.write_string(linha, 2, info[cod]['municipio'])
            ws_da.write_number(linha, 3, a)
            ws_da.write_string(linha, 4, info[cod]['faixa_porte'])
            for i in ORDEM_DADOS:
                x = v(cod, a, i)
                if x is None:
                    ws_da.write_string(linha, COL_DADOS[i], NA, f_cinza)
                else:
                    ws_da.write_number(linha, COL_DADOS[i], x, fnum(i))
            linha += 1
    n_da = linha - 1
    ws_da.set_column(0, 0, 12); ws_da.set_column(1, 1, 11); ws_da.set_column(2, 2, 28); ws_da.set_column(3, 3, 6)
    ws_da.set_column(4, 4, 20); ws_da.set_column(5, 12, 18)
    ws_da.set_row(0, 42)
    ws_da.freeze_panes(1, 3)
    ws_da.autofilter(0, 0, n_da, len(cab) - 1)
    R_DA = lambda c: f"'Dados'!${c}$2:${c}${n_da + 1}"
    col_da = {i: xl_col_to_name(COL_DADOS[i]) for i in ORDEM_DADOS}

    # ---------------------------------------------------------------- Referência
    cab = ['Chave', 'Faixa de porte', 'Ano', 'Indicador', 'Municípios com dado', 'Mínimo', '1º quartil', 'Mediana', '3º quartil', 'Máximo']
    ws_re.write_row(0, 0, cab, f_h)
    chaves_ref = sorted(ref.keys(), key=lambda k: (k[2], k[0], k[1]))
    for k, key in enumerate(chaves_ref, start=1):
        r = ref[key]
        ws_re.write_string(k, 0, f'{key[0]}|{key[1]}|{key[2]}')
        ws_re.write_string(k, 1, key[0])
        ws_re.write_number(k, 2, key[1])
        ws_re.write_string(k, 3, key[2])
        ws_re.write_number(k, 4, int(r['n']))
        for j, campo in enumerate(('minimo', 'p25', 'mediana', 'p75', 'maximo')):
            ws_re.write_number(k, 5 + j, float(r[campo]), f_n1)
    n_re = len(chaves_ref)
    ws_re.set_column(0, 0, 40); ws_re.set_column(1, 1, 20); ws_re.set_column(2, 2, 6); ws_re.set_column(3, 3, 20); ws_re.set_column(4, 9, 14)
    ws_re.set_row(0, 30)
    ws_re.freeze_panes(1, 0)
    R_RE = lambda c: f"'Referência'!${c}$2:${c}${n_re + 1}"

    # ---------------------------------------------------------------- Previsões
    cab = ['Chave', 'Código IBGE', 'Município', 'Ano', 'Previsto (R$ mi)', 'Inferior 80%', 'Superior 80%', 'Inferior 95%',
           'Superior 95%', 'Método', 'Grupo de porte do modelo']
    ws_pv.write_row(0, 0, cab, f_h)
    ordem_prev = sorted(prev.keys())
    for k, key in enumerate(ordem_prev, start=1):
        r = prev[key]
        ws_pv.write_string(k, 0, f'{key[0]}|{key[1]}')
        ws_pv.write_number(k, 1, key[0])
        ws_pv.write_string(k, 2, r['municipio'])
        ws_pv.write_number(k, 3, key[1])
        for j, campo in enumerate(('previsto', 'inferior_80', 'superior_80', 'inferior_95', 'superior_95')):
            ws_pv.write_number(k, 4 + j, float(r[campo]), f_n1)
        ws_pv.write_string(k, 9, r['metodo'])
        ws_pv.write_string(k, 10, r['grupo_porte'])
    n_pv = len(ordem_prev)
    ws_pv.set_column(0, 0, 14); ws_pv.set_column(1, 1, 11); ws_pv.set_column(2, 2, 28); ws_pv.set_column(3, 3, 6)
    ws_pv.set_column(4, 8, 14); ws_pv.set_column(9, 10, 22)
    ws_pv.set_row(0, 30)
    ws_pv.freeze_panes(1, 0)
    R_PV = lambda c: f"'Previsões'!${c}$2:${c}${n_pv + 1}"

    # ---------------------------------------------------------------- Painel
    ws = ws_pn
    ws.set_column(0, 0, 2); ws.set_column(1, 1, 42); ws.set_column(2, 2, 28); ws.set_column(3, 8, 16)
    ws.write('B1', 'Indicadores dos municípios de São Paulo', f_titulo)
    ws.write('B2', 'Escolha um município na célula amarela. Tudo abaixo e nas abas "Tabela do município" e "Previsão" se recalcula.', f_sub)
    ws.write('B4', 'Município (escolha na lista)', f_neg)
    ws.merge_range('C4:E4', nome_ex, f_in)
    ws.data_validation('C4', {'validate': 'list', 'source': f"={R_MU('B')}", 'error_title': 'Município não encontrado',
                              'error_message': 'Escolha um nome da lista.', 'input_title': 'Município',
                              'input_message': 'Escolha na lista ou digite o nome.'})
    n_na_faixa = sum(1 for r in dim_m if r['faixa_porte'] == faixa_ex)
    ws.write('B5', 'Código IBGE', f_txt)
    ws.write_formula('C5', f"=INDEX({R_MU('A')},MATCH($C$4,{R_MU('B')},0))", f_txt, cod_ex)
    ws.write('B6', 'Faixa de porte (municípios parecidos)', f_txt)
    ws.write_formula('C6', f"=INDEX({R_MU('C')},MATCH($C$4,{R_MU('B')},0))", f_txt, faixa_ex)
    ws.write('B7', 'Municípios na faixa', f_txt)
    ws.write_formula('C7', f"=COUNTIF({R_MU('C')},$C$6)", f_txt, n_na_faixa)
    ws.write('B8', 'População (Censo 2022)', f_txt)
    ws.write_formula('C8', f"=INDEX({R_MU('E')},MATCH($C$4,{R_MU('B')},0))", f_n0, int(info[cod_ex]['populacao_censo_2022']))
    ws.write('B9', 'Região geográfica imediata (IBGE)', f_txt)
    ws.write_formula('C9', f"=INDEX({R_MU('D')},MATCH($C$4,{R_MU('B')},0))", f_txt, info[cod_ex]['regiao_imediata'])

    # tabela do último valor
    ws.write('B11', 'Último valor de cada indicador, comparado com os municípios da faixa', f_neg)
    cab = ['Indicador', 'Unidade', 'Último ano com dado', 'Valor do município', 'Mediana da faixa', 'Diferença para a mediana',
           'Posição na faixa (0% a 100%)']
    ws.write_row(11, 1, cab, f_h)
    ws.set_row(11, 42)
    painel_inds = comum.INDICADORES_PAINEL
    # linhas da "Tabela do município" onde cada indicador começa
    TB0 = 9           # primeira linha (índice 0 = linha 1) do bloco do primeiro indicador: linha 10
    BLOCO = 6
    tb_linha = {i: TB0 + k * BLOCO for k, i in enumerate(painel_inds)}
    ANO0_COL = 2      # coluna C
    ult_col = ANO0_COL + len(ANOS) - 1
    rng_anos = f"$C$8:${xl_col_to_name(ult_col)}$8"       # linha 8 da tabela: os anos
    TBN = "'Tabela do município'"

    def ultimo_ano(i):
        anos_ok = [a for a in ANOS if v(cod_ex, a, i) is not None]
        return max(anos_ok) if anos_ok else None

    for k, i in enumerate(painel_inds):
        r = 12 + k       # índice de linha 0-based => linha Excel r+1
        xl = r + 1
        lin_v = tb_linha[i] + 1       # linha Excel do "valor do município"
        rv = f"{TBN}!$C${lin_v}:${xl_col_to_name(ult_col)}${lin_v}"
        ua = ultimo_ano(i)
        val = v(cod_ex, ua, i) if ua else None
        med = float(ref[(faixa_ex, ua, i)]['mediana']) if ua else None
        ws.write(r, 1, ind[i]['nome'], f_txt)
        ws.write(r, 2, ind[i]['unidade'], f_cinza)
        ws.write_formula(r, 3, f"=IFERROR(SUMPRODUCT(MAX(ISNUMBER({rv})*{TBN}!{rng_anos})),\"{NA}\")", fmt(num_format='0', align='center'), ua if ua else NA)
        ws.write_formula(r, 4, f"=IFERROR(INDEX({rv},MATCH(D{xl},{TBN}!{rng_anos},0)),\"{NA}\")", fnum(i), val if val is not None else NA)
        ws.write_formula(r, 5, f"=IFERROR(INDEX({R_RE('H')},MATCH($C$6&\"|\"&D{xl}&\"|{i}\",{R_RE('A')},0)),\"{NA}\")", fnum(i),
                         med if med is not None else NA)
        dif = (val / med - 1) if (val is not None and med) else NA
        ws.write_formula(r, 6, f"=IF(AND(ISNUMBER(E{xl}),ISNUMBER(F{xl})),E{xl}/F{xl}-1,\"{NA}\")", f_pct, dif)
        # posição: municípios da faixa com valor menor ÷ (n − 1); mesma conta do PERCENT_RANK do SQL
        if ua and val is not None:
            n = int(ref[(faixa_ex, ua, i)]['n'])
            menores = sum(1 for c in ordem_cod if info[c]['faixa_porte'] == faixa_ex and (v(c, ua, i) is not None) and v(c, ua, i) < val)
            pos = menores / (n - 1) if n > 1 else NA
        else:
            pos = NA
        ci = col_da[i]
        ws.write_formula(r, 7,
                         f"=IFERROR(COUNTIFS({R_DA('E')},$C$6,{R_DA('D')},D{xl},{R_DA(ci)},\"<\"&E{xl})/(INDEX({R_RE('E')},MATCH($C$6&\"|\"&D{xl}&\"|{i}\",{R_RE('A')},0))-1),\"{NA}\")",
                         f_pct0, pos)
    ws.merge_range(20, 1, 21, 7,
                   'Como ler: a mediana é a do grupo de municípios do mesmo porte (Censo 2022) no mesmo ano. "Posição" diz quantos '
                   'municípios da faixa têm valor menor: 0% é o menor valor, 100% é o maior. Estar acima ou abaixo da mediana não é, por si, '
                   'bom nem ruim: a gestão do município pode ter razão para o desvio.', f_aviso)

    # gráficos: dois por linha, a partir da linha 24
    wb_rows = {i: 62 + k * 4 for k, i in enumerate(painel_inds)}   # bloco de apoio na aba da tabela (ver abaixo)
    def grafico(i, linha_xl, col_xl):
        ch = wb.add_chart({'type': 'line'})
        lin = wb_rows[i]   # índice 0-based da linha "valor" no bloco de apoio
        cats = ['Tabela do município', 7, ANO0_COL, 7, ult_col]
        def serie(offset, nome, cor, largura, marcador=False, tracejado=None, transparencia=None):
            d = {'name': nome, 'categories': cats,
                 'values': ['Tabela do município', lin + offset, ANO0_COL, lin + offset, ult_col],
                 'line': {'color': cor, 'width': largura}}
            if tracejado:
                d['line']['dash_type'] = tracejado
            if marcador:
                d['marker'] = {'type': 'circle', 'size': 6, 'fill': {'color': cor}, 'border': {'color': '#FFFFFF', 'width': 1.25}}
            else:
                d['marker'] = {'type': 'none'}
            return d
        ch.add_series(serie(0, 'Município escolhido', AZUL, 2.25, marcador=True))
        ch.add_series(serie(1, 'Mediana da faixa', CINZA, 2))
        ch.add_series(serie(2, '1º quartil da faixa', CINZA_CLARO, 1))
        ch.add_series(serie(3, '3º quartil da faixa', CINZA_CLARO, 1))
        ch.set_title({'name': ind[i]['nome'], 'name_font': {'name': 'Arial', 'size': 11, 'bold': True, 'color': TINTA}, 'overlay': False})
        ch.set_x_axis({'num_font': {'name': 'Arial', 'size': 9, 'color': TINTA}, 'line': {'color': CINZA_CLARO}, 'major_tick_mark': 'none'})
        ch.set_y_axis({'num_font': {'name': 'Arial', 'size': 9, 'color': TINTA}, 'num_format': '#,##0.0' if int(ind[i]['casas']) else '#,##0',
                       'major_gridlines': {'visible': True, 'line': {'color': ZEBRA, 'width': 0.75}}, 'line': {'none': True},
                       'name': ind[i]['unidade'], 'name_font': {'name': 'Arial', 'size': 8, 'bold': False, 'color': CINZA}})
        ch.set_legend({'position': 'bottom', 'font': {'name': 'Arial', 'size': 8, 'color': TINTA}})
        ch.set_size({'width': 520, 'height': 290})
        ch.set_chartarea({'border': {'none': True}})
        ch.show_na_as_empty_cell()
        ch.show_blanks_as('gap')
        ws_pn.insert_chart(linha_xl - 1, col_xl, ch, {'object_position': 1})
    for k, i in enumerate(painel_inds):
        grafico(i, 24 + (k // 2) * 16, 1 if k % 2 == 0 else 4)
    ws.set_column(5, 5, 16)

    # ---------------------------------------------------------------- Tabela do município
    ws = ws_tb
    ws.set_column(0, 0, 40); ws.set_column(1, 1, 30); ws.set_column(2, ult_col, 10)
    ws.write('A1', 'Tabela do município', f_titulo)
    ws.write('A2', 'Município (escolhido na aba Painel)', f_neg)
    ws.write_formula('B2', "=Painel!$C$4", f_neg, nome_ex)
    ws.write('A3', 'Código IBGE', f_txt)
    ws.write_formula('B3', "=Painel!$C$5", f_txt, cod_ex)
    ws.write('A4', 'Faixa de porte', f_txt)
    ws.write_formula('B4', "=Painel!$C$6", f_txt, faixa_ex)
    ws.write('A5', 'As linhas "n.d." são anos em que a fonte não publica ou o município não declarou. Nenhum valor foi estimado.', f_cinza)
    ws.write(7, 0, 'Indicador', f_h)
    ws.write(7, 1, 'Linha', f_h)
    for j, a in enumerate(ANOS):
        ws.write_number(7, ANO0_COL + j, a, f_ano)
    # cabeçalhos de ano em linha 8 (índice 7). As fórmulas das células usam C$8.
    for i in painel_inds:
        r0 = tb_linha[i]
        casas_f = fnum(i)
        rotulos = ['Valor do município', 'Mediana da faixa', '1º quartil da faixa', '3º quartil da faixa', 'Diferença do município para a mediana']
        for j, rot in enumerate(rotulos):
            ws.write(r0 + j, 0, ind[i]['nome'] if j == 0 else '', f_neg if j == 0 else f_txt)
            ws.write(r0 + j, 1, rot, f_txt)
        for jj, a in enumerate(ANOS):
            col = ANO0_COL + jj
            L = xl_col_to_name(col)
            x = v(cod_ex, a, i)
            ws.write_formula(r0, col, f"=IFERROR(INDEX({R_DA(col_da[i])},MATCH($B$3&\"|\"&{L}$8,{R_DA('A')},0)),\"{NA}\")", casas_f,
                             x if x is not None else NA)
            rr = ref.get((faixa_ex, a, i))
            for j, campo in ((1, 'H'), (2, 'G'), (3, 'I')):
                chave = {'H': 'mediana', 'G': 'p25', 'I': 'p75'}[campo]
                val = float(rr[chave]) if rr else NA
                ws.write_formula(r0 + j, col,
                                 f"=IFERROR(INDEX({R_RE(campo)},MATCH($B$4&\"|\"&{L}$8&\"|{i}\",{R_RE('A')},0)),\"{NA}\")", casas_f, val)
            dv = (x / float(rr['mediana']) - 1) if (x is not None and rr and float(rr['mediana'])) else NA
            ws.write_formula(r0 + 4, col, f"=IF(AND(ISNUMBER({L}{r0 + 1}),ISNUMBER({L}{r0 + 2})),{L}{r0 + 1}/{L}{r0 + 2}-1,\"{NA}\")", f_pct, dv)
    # bloco de apoio aos gráficos: #N/D no lugar de "n.d.", para a linha ficar interrompida
    ap0 = 60
    ws.write(ap0 - 2, 0, 'Apoio aos gráficos do Painel (não editar)', f_neg)
    ws.write(ap0 - 1, 0, 'Os "#N/D" abaixo são propositais: é assim que o Excel deixa uma linha de gráfico interrompida onde não há dado.', f_cinza)
    for i in painel_inds:
        r_ap = wb_rows[i]
        for j, rot in enumerate(['Município escolhido', 'Mediana da faixa', '1º quartil da faixa', '3º quartil da faixa']):
            ws.write(r_ap + j, 0, ind[i]['nome'] if j == 0 else '', f_cinza)
            ws.write(r_ap + j, 1, rot, f_cinza)
            origem_linha = tb_linha[i] + j       # índice 0-based da linha de origem
            for jj, a in enumerate(ANOS):
                col = ANO0_COL + jj
                L = xl_col_to_name(col)
                if j == 0:
                    x = v(cod_ex, a, i)
                else:
                    rr = ref.get((faixa_ex, a, i))
                    x = float(rr[('mediana', 'p25', 'p75')[j - 1]]) if rr else None
                ws.write_formula(r_ap + j, col, f"=IF(ISNUMBER({L}{origem_linha + 1}),{L}{origem_linha + 1},NA())", f_apoio,
                                 x if x is not None else '#N/A')
    ws.freeze_panes(8, 2)

    # ---------------------------------------------------------------- Previsão
    ws = ws_pr
    ws.set_column(0, 0, 14); ws.set_column(1, 6, 16); ws.set_column(7, 7, 3); ws.set_column(8, 14, 12)
    ws.write('A1', 'Previsão da receita corrente do município', f_titulo)
    ws.write('A2', 'Município (escolhido na aba Painel)', f_neg)
    ws.write_formula('C2', "=Painel!$C$4", f_neg, nome_ex)
    ws.write('A3', 'Código IBGE', f_txt)
    ws.write_formula('C3', "=Painel!$C$5", f_txt, cod_ex)
    ws.write('A4', 'Grupo de porte do modelo', f_txt)
    grupo_ex = grupo_de_porte(int(info[cod_ex]['populacao_censo_2022']))
    ws.write_formula('C4', f"=INDEX({R_MU('F')},MATCH($C$2,{R_MU('B')},0))", f_txt, grupo_ex)
    ws.write_row(5, 0, ['Ano', 'Observado (R$ milhões de 2025)', 'Previsto', 'Inferior 80%', 'Superior 80%', 'Inferior 95%', 'Superior 95%'], f_h)
    ws.set_row(5, 42)
    anos_t = list(range(2015, 2029))
    r_ini = 6
    tem_prev = (cod_ex, 2028) in prev
    for k, a in enumerate(anos_t):
        r = r_ini + k
        xl = r + 1
        ws.write_number(r, 0, a, f_ano)
        obs = v(cod_ex, a, 'receita_total') if a <= 2025 else None
        if a <= 2025:
            ws.write_formula(r, 1, f"=IFERROR(INDEX({R_DA(col_da['receita_total'])},MATCH($C$3&\"|\"&A{xl},{R_DA('A')},0)),\"{NA}\")", f_n1,
                             obs if obs is not None else NA)
        else:
            ws.write(r, 1, '', f_n1)
        # colunas C..G: previsto, inf80, sup80, inf95, sup95. Em 2025 todas partem do valor observado (âncora).
        cols_pv = ['E', 'F', 'G', 'H', 'I']
        chaves_pv = ['previsto', 'inferior_80', 'superior_80', 'inferior_95', 'superior_95']
        for j, (cp, cv) in enumerate(zip(cols_pv, chaves_pv)):
            if a < 2025:
                ws.write(r, 2 + j, '', f_n1)
            elif a == 2025:
                ws.write_formula(r, 2 + j, f"=B{xl}", f_n1, obs if obs is not None else NA)
            else:
                x = float(prev[(cod_ex, a)][cv]) if (cod_ex, a) in prev else NA
                ws.write_formula(r, 2 + j,
                                 f"=IFERROR(INDEX({R_PV(cp)},MATCH($C$3&\"|\"&A{xl},{R_PV('A')},0)),\"{NA}\")", f_n1, x)
    ult = r_ini + len(anos_t) - 1
    # apoio (NA) ao lado, colunas I..O
    ws.write(4, 8, 'Apoio ao gráfico (não editar)', f_cinza)
    ws.write_row(5, 8, ['Ano', 'Observado', 'Previsto', 'Inf. 80%', 'Sup. 80%', 'Inf. 95%', 'Sup. 95%'], f_cinza)
    for k, a in enumerate(anos_t):
        r = r_ini + k
        xl = r + 1
        ws.write_formula(r, 8, f"=A{xl}", f_apoio, a)
        for j in range(6):
            src = xl_col_to_name(1 + j)
            if j == 0:
                x = v(cod_ex, a, 'receita_total') if a <= 2025 else None
            else:
                x = None
                if a == 2025:
                    x = v(cod_ex, 2025, 'receita_total')
                elif a > 2025 and (cod_ex, a) in prev:
                    x = float(prev[(cod_ex, a)][chaves_pv[j - 1]])
            ws.write_formula(r, 9 + j, f"=IF(ISNUMBER({src}{xl}),{src}{xl},NA())", f_apoio, x if x is not None else '#N/A')
    # frase de leitura
    p28 = prev.get((cod_ex, 2028))
    if p28:
        frase = (f"Em 2028, a receita corrente de {nome_ex} fica perto de R$ {round(float(p28['previsto']))} milhões "
                 f"(a preços de 2025). Na faixa de 80% do teste do passado, entre R$ {round(float(p28['inferior_80']))} e "
                 f"R$ {round(float(p28['superior_80']))} milhões; na de 95%, entre R$ {round(float(p28['inferior_95']))} e "
                 f"R$ {round(float(p28['superior_95']))} milhões.")
    else:
        frase = NA
    ws.write(r_ini + len(anos_t) + 1, 0, 'Leitura', f_neg)
    ws.merge_range(r_ini + len(anos_t) + 2, 0, r_ini + len(anos_t) + 3, 6, '', f_aviso)
    ws.write_formula(r_ini + len(anos_t) + 2, 0,
                     f"=IFERROR(\"Em 2028, a receita corrente de \"&$C$2&\" fica perto de R$ \"&ROUND(C{ult + 1},0)&\" milhões (a preços de 2025). Na faixa de 80% do teste do passado, entre R$ \"&ROUND(D{ult + 1},0)&\" e R$ \"&ROUND(E{ult + 1},0)&\" milhões; na de 95%, entre R$ \"&ROUND(F{ult + 1},0)&\" e R$ \"&ROUND(G{ult + 1},0)&\" milhões.\",\"Este município não tem os cinco últimos anos de receita válidos: sem previsão.\")",
                     f_aviso, frase)
    ch = wb.add_chart({'type': 'line'})
    cats = ['Previsão', r_ini, 8, ult, 8]
    def s(j, nome, cor, larg, dash=None, marcador=False):
        d = {'name': nome, 'categories': cats, 'values': ['Previsão', r_ini, 9 + j, ult, 9 + j],
             'line': {'color': cor, 'width': larg}, 'marker': {'type': 'none'}}
        if dash:
            d['line']['dash_type'] = dash
        if marcador:
            d['marker'] = {'type': 'circle', 'size': 6, 'fill': {'color': cor}, 'border': {'color': '#FFFFFF', 'width': 1.25}}
        return d
    ch.add_series(s(0, 'Observado', AZUL, 2.25, marcador=True))
    ch.add_series(s(1, 'Previsto', AZUL, 2.25, dash='dash'))
    ch.add_series(s(2, 'Faixa de 80%', AZUL, 1))
    ch.add_series(s(3, 'Limite superior de 80%', AZUL, 1))
    ch.add_series(s(4, 'Faixa de 95%', CINZA, 1, dash='round_dot'))
    ch.add_series(s(5, 'Limite superior de 95%', CINZA, 1, dash='round_dot'))
    ch.set_title({'name': 'Receita corrente, R$ milhões de 2025: observado e previsto', 'name_font': {'name': 'Arial', 'size': 11, 'bold': True, 'color': TINTA}})
    ch.set_x_axis({'num_font': {'name': 'Arial', 'size': 9}, 'line': {'color': CINZA_CLARO}, 'major_tick_mark': 'none'})
    ch.set_y_axis({'num_font': {'name': 'Arial', 'size': 9}, 'num_format': '#,##0', 'line': {'none': True},
                   'major_gridlines': {'visible': True, 'line': {'color': ZEBRA, 'width': 0.75}}})
    ch.set_legend({'position': 'bottom', 'font': {'name': 'Arial', 'size': 8}, 'delete_series': [3, 5]})
    ch.set_size({'width': 640, 'height': 340})
    ch.set_chartarea({'border': {'none': True}})
    ch.show_na_as_empty_cell()
    ch.show_blanks_as('gap')
    ws.insert_chart(r_ini + len(anos_t) + 5, 0, ch)

    # texto do modelo e do teste (valores do teste vêm de dados/tratados/backtest_*.csv)
    r = r_ini + len(anos_t) + 24
    ws.write(r, 0, 'Como a previsão foi feita', f_neg)
    metodo = next(m['metodo'] for m in bt_m if m['escolhido'] == '1')
    esc = {int(q['nivel']): float(q['escala']) for q in comum.ler_csv('modelo_quantis.csv')}
    texto = [
        f'Série: receita corrente líquida de deduções, em R$ milhões de 2025 (IPCA), de 2015 a 2025. Método escolhido: "{metodo}", sobre o logaritmo da série.',
        'Três métodos simples concorreram: repetir o último valor, estender a tendência dos 3 últimos anos e estender uma reta ajustada aos 5 últimos anos. '
        'Cada um foi testado prevendo o passado (origens de 2019 a 2022, 1 a 3 anos à frente) em todos os municípios com série completa; ficou o de menor erro.',
        'A faixa de incerteza não é fórmula de livro: vem dos erros que o método de fato cometeu, por horizonte e por grupo de porte. '
        'A receita dos municípios se move junta de um ano para o outro (inflação, ICMS, transferências), então os quatro anos de origem do teste '
        'são quatro "choques" e não 600 observações independentes. Por isso a faixa foi testada deixando uma origem de fora e alargada '
        f'(fator {esc.get(80, 1):.2f} para a de 80% e {esc.get(95, 1):.2f} para a de 95%) até a cobertura do teste chegar ao nível prometido.',
        'Limites: método sem informação de fora da série; não conhece mudança de lei, de convênio ou de gestão. Depois do ajuste, a cobertura '
        'ficou perto do nível prometido na média, mas com a origem 2022 de fora a faixa de 80% cobriu bem menos (tabela abaixo): um ano '
        'que vem depois de um salto de receita (2022) é mais difícil de prever. A Revisão técnica por estatístico registrado no CONRE ainda não está registrada para esta amostra.',
    ]
    for k, t in enumerate(texto, start=1):
        ws.merge_range(r + k, 0, r + k, 6, t, f_txt)
        ws.set_row(r + k, 62 if len(t) > 330 else 46)
    r2 = r + len(texto) + 2
    ws.write(r2, 0, 'Erro do método, ao prever o passado', f_neg)
    ws.write_row(r2 + 1, 0, ['Método', 'Anos à frente', 'Previsões testadas', 'Erro médio absoluto (%)', 'Viés (%)', 'Escolhido'], f_h)
    for k, m in enumerate(bt_m, start=1):
        ws.write(r2 + 1 + k, 0, m['metodo'])
        ws.write_number(r2 + 1 + k, 1, int(m['horizonte']))
        ws.write_number(r2 + 1 + k, 2, int(m['n']), f_n0)
        ws.write_number(r2 + 1 + k, 3, float(m['erro_medio_abs_pct']), f_n1)
        ws.write_number(r2 + 1 + k, 4, float(m['vies_pct']), f_n1)
        ws.write(r2 + 1 + k, 5, 'sim' if m['escolhido'] == '1' else '')
    r3 = r2 + len(bt_m) + 3
    ws.write(r3, 0, 'Quanto da realidade caiu dentro da faixa, deixando uma origem de fora', f_neg)
    ws.write_row(r3 + 1, 0, ['Nível da faixa (%)', 'Origem que ficou de fora', 'Valores testados', 'Dentro, sem ajuste (%)', 'Dentro, com ajuste (%)'], f_h)
    ws.set_row(r3 + 1, 30)
    k = 0
    for nv in (80, 95):
        for T0 in sorted({int(m['origem_fora']) for m in bt_c}):
            ll = [m for m in bt_c if int(m['nivel']) == nv and int(m['origem_fora']) == T0]
            n = sum(int(m['n_teste']) for m in ll)
            k += 1
            ws.write_number(r3 + 1 + k, 0, nv)
            ws.write_number(r3 + 1 + k, 1, T0)
            ws.write_number(r3 + 1 + k, 2, n, f_n0)
            ws.write_number(r3 + 1 + k, 3, sum(float(m['cobertura_sem_ajuste']) * int(m['n_teste']) for m in ll) / n, f_n1)
            ws.write_number(r3 + 1 + k, 4, sum(float(m['cobertura_com_ajuste']) * int(m['n_teste']) for m in ll) / n, f_n1)

    # ---------------------------------------------------------------- Indicadores (definição escrita)
    ws = ws_in
    ws.write('A1', 'Indicadores: definição escrita', f_titulo)
    ws.write('A2', 'Cada Indicador tem fórmula, fonte, periodicidade e meta escritas. Sem isso, dois analistas calculam números diferentes com o mesmo nome.', f_sub)
    ws.write_row(3, 0, ['Indicador', 'Unidade', 'Fórmula', 'Fonte', 'Periodicidade', 'Meta', 'Leitura de apoio'], f_h)
    leitura = {'neutro': 'Mais ou menos depende da escolha do município; não é acerto nem erro.',
               'maior': 'Valor maior costuma indicar situação mais favorável, mas leia com o contexto.'}
    for k, r in enumerate(dim_i, start=4):
        ws.write(k, 0, r['nome'], f_neg)
        ws.write(k, 1, r['unidade'], f_txt)
        ws.write(k, 2, r['formula'], f_txt)
        ws.write(k, 3, r['fonte'], f_txt)
        ws.write(k, 4, r['periodicidade'], f_txt)
        ws.write(k, 5, r['meta'], f_txt)
        ws.write(k, 6, leitura[r['sentido']], f_txt)
        ws.set_row(k, 62)
    ws.set_column(0, 0, 30); ws.set_column(1, 1, 24); ws.set_column(2, 3, 48); ws.set_column(4, 5, 30); ws.set_column(6, 6, 36)
    ws.write(len(dim_i) + 5, 0, 'Municípios parecidos: a faixa de porte', f_neg)
    ws.merge_range(len(dim_i) + 6, 0, len(dim_i) + 6, 6,
                   'Municípios parecidos são os da mesma faixa de população do Censo 2022: até 5 mil, de 5 a 10 mil, de 10 a 20 mil, de 20 a 50 mil, '
                   'de 50 a 100 mil, de 100 a 500 mil e mais de 500 mil habitantes. Porte é só um critério: dois municípios do mesmo porte podem ter '
                   'estruturas muito diferentes (turismo, indústria, região metropolitana). Use a comparação como ponto de partida para perguntas, e não como veredito.', f_txt)
    ws.set_row(len(dim_i) + 6, 48)

    # ---------------------------------------------------------------- Fontes e licenças
    ws = ws_fo
    ws.write('A1', 'Fontes, licenças e como cada uma foi verificada', f_titulo)
    ws.write('A2', 'Consulta feita em 14/10/2026. "Verificado" quer dizer que o texto da página foi lido nesse dia; "não verificado" quer dizer que não consegui ler o texto da licença da base.', f_sub)
    ws.write_row(3, 0, ['Base', 'Órgão', 'O que foi usado', 'Endereço', 'Condição de uso encontrada', 'Situação da verificação'], f_h)
    fontes = [
        ('Declaração de Contas Anuais (DCA), anexos I-C e I-E', 'Tesouro Nacional (Siconfi)', 'Receitas correntes, deduções, transferências e despesa por função, 2015 a 2025',
         'https://apidatalake.tesouro.gov.br/docs/siconfi/',
         'A página de APIs do Tesouro diz que os dados são "disponibilizados para livre utilização". Não encontrei na página uma instrução de citação.',
         'Verificado em https://www.gov.br/tesouronacional/pt-br/central-de-conteudo/apis (14/10/2026). Texto de licença formal da base: não encontrado.'),
        ('Estimativas da população (tabela 6579) e Censo 2022 (tabela 9514)', 'IBGE (SIDRA)', 'População residente por município',
         'https://apisidra.ibge.gov.br/', 'Dado aberto de órgão federal, sujeito ao Decreto 8.777/2016: "licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte".',
         'Páginas de termos de uso do IBGE bloqueiam acesso automatizado (HTTP 403); o texto próprio do IBGE não foi lido. A condição acima vem do Decreto.'),
        ('Produto Interno Bruto dos Municípios (tabela 5938)', 'IBGE (SIDRA)', 'PIB a preços correntes, 2015 a 2023', 'https://apisidra.ibge.gov.br/',
         'Igual à linha anterior.', 'Igual à linha anterior.'),
        ('IPCA, número-índice (tabela 1737)', 'IBGE (SIDRA)', 'Deflator mensal, 2015 a 2025', 'https://apisidra.ibge.gov.br/', 'Igual às linhas do IBGE.', 'Igual às linhas do IBGE.'),
        ('Lista de municípios e regiões geográficas imediatas', 'IBGE (API de Localidades)', 'Nome, código e região', 'https://servicodados.ibge.gov.br/api/docs',
         'Igual às linhas do IBGE.', 'Igual às linhas do IBGE.'),
        ('Ideb, anos iniciais, por município (divulgação 2023)', 'INEP', 'Ideb observado de 2015 a 2023, rede municipal',
         'https://download.inep.gov.br/ideb/resultados/divulgacao_anos_iniciais_municipios_2023.xlsx',
         'A Política de Dados Abertos do Inep (Portaria nº 380/2020) define dados abertos como os disponibilizados "sob licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar sua autoria ou a fonte". O CC BY 4.0 como licença padrão aparece em fonte secundária (Portaria nº 496/2021).',
         'Portaria 380/2020 lida no PDF da política do Inep (14/10/2026). A Portaria 496/2021 não foi lida em fonte primária.'),
        ('SINASC: Declarações de Nascido Vivo, arquivos DNSP de 2015 a 2024', 'Ministério da Saúde (DataSUS)', 'Contagem de nascidos vivos por consultas de pré-natal e município de residência da mãe',
         'ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/',
         'A página do Ministério diz que "os dados estão disponíveis de forma pública e anonimizada". O rodapé dos sites do Ministério traz "Creative Commons Atribuição-SemDerivações 3.0" para o conteúdo do site, não declarado para os arquivos de dados.',
         'Páginas lidas em 14/10/2026. A licença do arquivo de microdados não está escrita no FTP; a condição vem do Decreto 8.777/2016 (credite a fonte).'),
    ]
    for k, row in enumerate(fontes, start=4):
        for j, t in enumerate(row):
            ws.write(k, j, t, f_txt)
        ws.set_row(k, 92)
    ws.set_column(0, 0, 34); ws.set_column(1, 1, 22); ws.set_column(2, 2, 32); ws.set_column(3, 3, 38); ws.set_column(4, 5, 52)
    ws.merge_range(len(fontes) + 5, 0, len(fontes) + 5, 5,
                   'Pendente: ler o texto de licença próprio de cada órgão (IBGE e Tesouro em especial) antes de a amostra ser publicada fora da Shark, e '
                   'validar a redação da atribuição com advogado. Esta aba não é parecer jurídico.', f_aviso)
    ws.set_row(len(fontes) + 5, 36)

    # ---------------------------------------------------------------- Leia-me
    ws = ws_leia
    ws.set_column(0, 0, 3); ws.set_column(1, 1, 110)
    ws.write('B1', 'Indicadores dos municípios de São Paulo: Entregável de amostra', f_titulo)
    linhas = [
        ('O que é', 'Uma planilha que junta, para os 645 municípios de SP, oito indicadores de finanças, educação, saúde e economia, de 2015 a 2025, e compara cada município com os de mesmo porte. '
                    'Tem ainda uma previsão simples da receita, com a incerteza à vista.'),
        ('O que não é', 'Não é trabalho feito para um Cliente nem avaliação de nenhuma prefeitura. É uma amostra feita com dado público, para mostrar como a entrega chega às mãos de quem compra. '
                        'Nenhum número aqui é resultado de Cliente.'),
        ('Como usar', '1) Vá à aba "Painel". 2) Escolha o município na célula amarela. 3) Leia a tabela, os gráficos e, em "Previsão", a projeção da receita. '
                      'As abas "Dados", "Referência", "Previsões" e "Municípios" guardam os números de origem; as demais abas são fórmulas sobre elas.'),
        ('Como conferir um número', 'Cada fórmula aponta para a aba "Dados" ou "Referência". Cada linha de "Dados" vem do arquivo indicadores_longo.csv, que as consultas SQL do repositório geram. '
                                    'O README do repositório explica, indicador por indicador, o caminho do número bruto até a célula.'),
        ('Como ler a comparação', 'A mediana é a dos municípios do mesmo porte (Censo 2022) no mesmo ano. A posição vai de 0% (menor valor da faixa) a 100% (maior). '
                                  'Estar acima ou abaixo não é bom nem ruim por si: depende de escolhas e de contexto do município.'),
        ('Cuidados', '• Valores em reais de 2025 (IPCA). • Os indicadores por habitante têm um degrau entre 2021 e 2022: a população de 2015 a 2021 é projeção do Censo 2010 e a de 2022 em diante vem do Censo 2022. '
                     'A série de receita total (R$ milhões) não tem esse degrau. • O Ideb é bienal, e município sem rede municipal fica sem Ideb. • O PIB municipal termina em 2023. '
                     '• Município que não entregou a declaração ao Tesouro no ano fica "n.d.": nada foi estimado.'),
        ('Revisão técnica', 'Todo Entregável de um Projeto passa por Revisão técnica de estatístico registrado no CONRE. Para esta amostra, feita com dado público, a revisão ainda não está registrada.'),
        ('Fontes', 'Tesouro Nacional (Siconfi), IBGE, INEP e DataSUS. Licenças e como cada uma foi verificada: aba "Fontes e licenças".'),
    ]
    r = 2
    for titulo, texto in linhas:
        ws.write(r, 1, titulo, f_neg)
        ws.write(r + 1, 1, texto, f_txt)
        ws.set_row(r + 1, 15 * max(2, int(len(texto) / 105) + 1))
        r += 3

    wb.close()
    print('gravado', SAIDA)


if __name__ == '__main__':
    main()
