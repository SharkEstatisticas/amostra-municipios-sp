"""Coleta 4 de 4: Ideb dos anos iniciais, rede municipal, por município de SP (INEP).

Baixa a planilha de divulgação do Ideb 2023 (a série 2005 a 2023 vem na mesma planilha) e
guarda o Ideb observado de 2015 a 2023 dos municípios de SP, só da rede municipal.
Município sem rede municipal (ou sem resultado) fica sem valor: "-" na planilha vira vazio.
Uso: python coletar_ideb.py
"""
import csv, os, urllib.request
import openpyxl

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(RAIZ, 'dados', 'brutos')
URL = 'https://download.inep.gov.br/ideb/resultados/divulgacao_anos_iniciais_municipios_2023.xlsx'
ANOS = [2015, 2017, 2019, 2021, 2023]


def main():
    arq = os.path.join(BRUTOS, 'ideb_anos_iniciais_municipios_2023.xlsx')
    if not os.path.exists(arq):
        req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=300) as r, open(arq, 'wb') as f:
            f.write(r.read())
    wb = openpyxl.load_workbook(arq, read_only=True)
    linhas = wb.worksheets[0].iter_rows(values_only=True)
    cab = None
    saida = []
    for i, r in enumerate(linhas):
        if i == 9:  # linha dos nomes de coluna (SG_UF, CO_MUNICIPIO, ...)
            cab = {nome: j for j, nome in enumerate(r) if isinstance(nome, str)}
            continue
        if cab is None or r[0] != 'SP' or r[cab['REDE']] != 'Municipal':
            continue
        for ano in ANOS:
            v = r[cab[f'VL_OBSERVADO_{ano}']]
            saida.append((r[cab['CO_MUNICIPIO']], ano, v if isinstance(v, (int, float)) else ''))
    with open(os.path.join(BRUTOS, 'ideb_municipio_ano.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cod_ibge', 'ano', 'ideb_anos_iniciais_municipal'])
        w.writerows(saida)
    print(len(saida), 'linhas')


if __name__ == '__main__':
    main()
