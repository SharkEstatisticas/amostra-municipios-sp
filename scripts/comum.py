"""Partes comuns dos scripts: caminhos, cores do site e o município de exemplo."""
import csv
import os
import random
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRATADOS = os.path.join(RAIZ, 'dados', 'tratados')
GRAFICOS = os.path.join(RAIZ, 'graficos')
EXCEL = os.path.join(RAIZ, 'excel')
CORES_TS = os.path.join(RAIZ, 'identidade', 'cores.ts')

# Sorteio do município de exemplo: semente fixa (a data da sessão), entre os que têm série completa.
SEMENTE = 20261014
INDICADORES_PAINEL = ['receita_pc', 'dependencia_transf', 'saude_pc', 'educacao_pc', 'pib_pc', 'ideb', 'pre_natal_7mais']
ANOS = list(range(2015, 2026))


def cores():
    """Lê as cores de identidade/cores.ts, a fonte única da paleta (nada é copiado à mão)."""
    with open(CORES_TS, encoding='utf-8') as f:
        texto = f.read()
    return {nome: valor for nome, valor in re.findall(r"^\s*([a-zA-Z]+):\s*'(#[0-9A-Fa-f]{6})'", texto, flags=re.M)}


def ler_csv(arquivo):
    with open(os.path.join(TRATADOS, arquivo), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def municipio_de_exemplo():
    """Sorteia, com semente fixa, um município com receita, saúde, educação, dependência, pré-natal e
    PIB de 2015 a 2022 e Ideb nos cinco anos: um exemplo sem escolha nossa do que ele mostra."""
    dados = {}
    for r in ler_csv('indicadores_longo.csv'):
        dados.setdefault(int(r['cod_ibge']), {}).setdefault(r['indicador_id'], set()).add(int(r['ano']))
    exigencias = {'receita_pc': set(ANOS), 'dependencia_transf': set(ANOS), 'saude_pc': set(ANOS),
                  'educacao_pc': set(ANOS), 'pre_natal_7mais': set(range(2015, 2025)),
                  'ideb': {2015, 2017, 2019, 2021, 2023}, 'pib_pc': set(range(2015, 2024))}
    candidatos = sorted(c for c, d in dados.items()
                        if all(ind in d and anos <= d[ind] for ind, anos in exigencias.items()))
    return random.Random(SEMENTE).choice(candidatos), len(candidatos)
