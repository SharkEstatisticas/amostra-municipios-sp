"""Coleta 3 de 4: IBGE, API SIDRA (população, PIB municipal e IPCA).

- Tabela 6579 (v 9324): população residente estimada, por município (2015 a 2021 e 2024 a 2026).
- Tabela 9514 (v 93): população residente, Censo 2022.
- Tabela 5938 (v 37): PIB a preços correntes, em R$ mil, por município (último ano publicado: 2023).
- Tabela 1737 (v 2266): IPCA, número-índice (dez/1993 = 100), mensal, Brasil: o deflator.
Uso: python coletar_sidra.py
"""
import csv, gzip, json, os, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(RAIZ, 'dados', 'brutos')
BASE = 'https://apisidra.ibge.gov.br/values'
SP = 'n6/in%20n3%2035'


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        corpo = r.read()
    if corpo[:2] == bytes([0x1F, 0x8B]):
        corpo = gzip.decompress(corpo)
    return json.loads(corpo.decode('utf-8'))[1:]  # a primeira linha é o cabeçalho


def gravar(nome, campos, linhas):
    with open(os.path.join(BRUTOS, nome), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(campos)
        w.writerows(linhas)
    print(nome, len(linhas), 'linhas')


def numero(v):
    return None if v in ('...', '-', 'X', '..') else v


def main():
    pop = [(r['D1C'], r['D3C'], numero(r['V'])) for r in get(f'{BASE}/t/6579/{SP}/v/9324/p/all')]
    gravar('ibge_populacao_estimada.csv', ['cod_ibge', 'ano', 'populacao'], pop)
    censo = [(r['D1C'], r['D3C'], numero(r['V'])) for r in get(f'{BASE}/t/9514/{SP}/v/93/p/2022/c2/6794/c287/100362/c286/113635')]
    gravar('ibge_populacao_censo2022.csv', ['cod_ibge', 'ano', 'populacao'], censo)
    pib = [(r['D1C'], r['D3C'], numero(r['V'])) for r in get(f'{BASE}/t/5938/{SP}/v/37/p/all')]
    gravar('ibge_pib_corrente_mil_reais.csv', ['cod_ibge', 'ano', 'pib_mil_reais'], pib)
    ipca = [(r['D3C'], numero(r['V'])) for r in get(f'{BASE}/t/1737/n1/all/v/2266/p/201501-202512')]
    gravar('ibge_ipca_indice.csv', ['mes', 'indice'], ipca)


if __name__ == '__main__':
    main()
