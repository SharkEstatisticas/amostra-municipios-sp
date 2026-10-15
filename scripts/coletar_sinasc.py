"""Coleta 1 de 4: nascidos vivos por município de residência da mãe (SINASC, DataSUS).

Baixa DNSP<ano>.dbc do FTP público do DataSUS, descomprime (dbc.py), conta por município:
  nascidos vivos, com pré-natal informado, com 7 ou mais consultas, partos cesáreos.
Grava dados/brutos/sinasc_municipio_ano.csv (pequeno, vai ao git). O .dbc bruto fica fora do git.
Uso: python coletar_sinasc.py [ano_inicial] [ano_final]
"""
import csv, sys, time, urllib.request, os
from collections import defaultdict
import dbc

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(RAIZ, 'dados', 'brutos')
URL = 'ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/DNSP{ano}.dbc'


def contar(caminho):
    campos, dbf, tam_cab, tam_reg, n = dbc.ler_dbc(caminho)
    pos, off = {}, 1
    for nome, _, tam in campos:
        pos[nome] = (off, tam)
        off += tam
    (m0, m1), (c0, c1), (p0, p1) = (pos[k] for k in ('CODMUNRES', 'CONSULTAS', 'PARTO'))
    m1 += m0; c1 += c0; p1 += p0
    cont = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # nascidos, cons.informadas, cons.7+, parto informado, cesareo, 0
    for i in range(n):
        base = tam_cab + i * tam_reg
        reg = dbf[base:base + tam_reg]
        mun = reg[m0:m1].decode('latin-1').strip()  # o DBF completa com espaços
        c = cont[mun]
        c[0] += 1
        cons = reg[c0:c1].strip()
        if cons in (b'1', b'2', b'3', b'4'):
            c[1] += 1
            if cons == b'4':
                c[2] += 1
        parto = reg[p0:p1].strip()
        if parto in (b'1', b'2'):
            c[3] += 1
            if parto == b'2':
                c[4] += 1
    return n, cont


def main():
    ini = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    fim = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    saida = os.path.join(BRUTOS, 'sinasc_municipio_ano.csv')
    linhas = []
    if os.path.exists(saida):
        with open(saida, encoding='utf-8', newline='') as f:
            linhas = [r for r in csv.DictReader(f)]
    feitos = {int(r['ano']) for r in linhas}
    for ano in range(ini, fim + 1):
        if ano in feitos:
            continue
        arq = os.path.join(BRUTOS, f'DNSP{ano}.dbc')
        if not os.path.exists(arq):
            try:
                urllib.request.urlretrieve(URL.format(ano=ano), arq)
            except Exception as e:  # ano ainda não publicado
                print(ano, 'indisponível:', e, flush=True)
                continue
        t = time.time()
        n, cont = contar(arq)
        for mun, c in cont.items():
            linhas.append(dict(ano=ano, cod_municipio6=mun, nascidos=c[0], pre_natal_informado=c[1],
                               pre_natal_7mais=c[2], parto_informado=c[3], parto_cesareo=c[4]))
        print(ano, n, 'registros,', len(cont), 'municípios,', round(time.time() - t), 's', flush=True)
        with open(saida, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['ano', 'cod_municipio6', 'nascidos', 'pre_natal_informado',
                                              'pre_natal_7mais', 'parto_informado', 'parto_cesareo'])
            w.writeheader()
            w.writerows(sorted(linhas, key=lambda r: (int(r['ano']), r['cod_municipio6'])))


if __name__ == '__main__':
    main()
