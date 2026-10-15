"""Coleta 2 de 4: finanças municipais (Siconfi/Tesouro) e a lista de municípios (IBGE).

- IBGE Localidades: 645 municípios de SP com a região geográfica imediata (grupo de comparação).
- Siconfi, API de dados abertos, endpoint /dca (Declaração de Contas Anuais), por município e ano:
    Anexo I-C (receitas orçamentárias) e Anexo I-E (despesas por função).
Grava só os valores que viram Indicador (dados/brutos/siconfi_municipio_ano.csv); a resposta
completa da API (centenas de linhas por município) não é guardada: refazer é rodar este script.
Uso: python coletar_siconfi_ibge.py [ano_inicial] [ano_final]
"""
import csv, gzip, json, os, re, sys, threading, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(RAIZ, 'dados', 'brutos')
API = 'https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca'
CAMPOS = ['ano', 'cod_ibge', 'entregou_ic', 'entregou_ie', 'populacao', 'rc_bruta', 'ded_fundeb', 'outras_ded',
          'transf_correntes', 'saude_empenhada', 'educacao_empenhada']


_TRAVA = threading.Lock()
_ULTIMO = [0.0]
_FRIO = [0.0]       # depois de um 429, todas as threads esperam juntas
INTERVALO = 0.35   # a API do Tesouro devolve 429 acima de uns 3 pedidos por segundo


def _esperar_vez():
    with _TRAVA:
        agora = time.time()
        espera = max(_ULTIMO[0] + INTERVALO, _FRIO[0]) - agora
        if espera > 0:
            time.sleep(espera)
        _ULTIMO[0] = time.time()


def get_json(url, tentativas=12):
    for t in range(tentativas):
        _esperar_vez()
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                corpo = r.read()
            if corpo[:2] == bytes([0x1F, 0x8B]):  # o IBGE responde comprimido
                corpo = gzip.decompress(corpo)
            return json.loads(corpo.decode('utf-8'))
        except Exception:
            if t == tentativas - 1:
                raise
            time.sleep(2 * (t + 1))


def municipios():
    arq = os.path.join(BRUTOS, 'municipios_sp.csv')
    if not os.path.exists(arq):
        d = get_json('https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios')
        with open(arq, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['cod_ibge', 'municipio', 'regiao_imediata', 'regiao_intermediaria'])
            for m in sorted(d, key=lambda m: m['id']):
                ri = m.get('regiao-imediata') or {}
                rint = (ri.get('regiao-intermediaria') or {})
                w.writerow([m['id'], m['nome'], ri.get('nome', ''), rint.get('nome', '')])
    with open(arq, encoding='utf-8', newline='') as f:
        return [int(r['cod_ibge']) for r in csv.DictReader(f)]


def codigo4(conta):
    """'1.7.0.0.00.0.0 - Transferências...' -> '1.7.0.0' se o resto do código é zero; senão None."""
    m = re.match(r'^(\d(?:\.\d+)*)\s*-', conta)
    if not m:
        return None
    partes = m.group(1).split('.')
    if len(partes) < 4 or any(int(p) != 0 for p in partes[4:]):
        return None
    return '.'.join(partes[:4])


def consultar(ano, ente):
    linha = dict.fromkeys(CAMPOS)
    linha.update(ano=ano, cod_ibge=ente, entregou_ic=0, entregou_ie=0)
    base = f'{API}?an_exercicio={ano}&id_ente={ente}&no_anexo='
    ic = get_json(base + urllib.parse.quote('DCA-Anexo I-C'))['items']
    ie = get_json(base + urllib.parse.quote('DCA-Anexo I-E'))['items']
    if ic:
        linha['entregou_ic'] = 1
        linha['populacao'] = ic[0].get('populacao')
        soma = {'rc_bruta': 0.0, 'ded_fundeb': 0.0, 'outras_ded': 0.0, 'transf_correntes': 0.0}
        for i in ic:
            c = codigo4(i['conta'])
            if c == '1.0.0.0':
                if i['coluna'] == 'Receitas Brutas Realizadas': soma['rc_bruta'] += i['valor']
                elif i['coluna'] == 'Deduções - FUNDEB': soma['ded_fundeb'] += i['valor']
                elif i['coluna'] == 'Outras Deduções da Receita': soma['outras_ded'] += i['valor']
            elif c == '1.7.0.0' and i['coluna'] == 'Receitas Brutas Realizadas':
                soma['transf_correntes'] += i['valor']
        linha.update(soma)
    if ie:
        linha['entregou_ie'] = 1
        if linha['populacao'] is None:
            linha['populacao'] = ie[0].get('populacao')
        s = e = 0.0
        for i in ie:
            if i['coluna'] != 'Despesas Empenhadas':
                continue
            if i['conta'] == '10 - Saúde': s += i['valor']
            elif i['conta'] == '12 - Educação': e += i['valor']
        linha.update(saude_empenhada=s, educacao_empenhada=e)
    return linha


def main():
    ini = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    fim = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    entes = municipios()
    saida = os.path.join(BRUTOS, 'siconfi_municipio_ano.csv')
    feitos = set()
    if os.path.exists(saida):
        with open(saida, encoding='utf-8', newline='') as f:
            feitos = {(int(r['ano']), int(r['cod_ibge'])) for r in csv.DictReader(f)}
    novo = not os.path.exists(saida)
    tarefas = [(a, e) for a in range(ini, fim + 1) for e in entes if (a, e) not in feitos]
    print(len(tarefas), 'consultas', flush=True)
    falhas = []
    with open(saida, 'a', encoding='utf-8', newline='') as f, ThreadPoolExecutor(6) as ex:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        futuros = {ex.submit(consultar, *t): t for t in tarefas}
        for k, fut in enumerate(as_completed(futuros), 1):
            try:
                w.writerow(fut.result())
            except Exception as erro:  # fica de fora; a próxima execução refaz só o que falta
                falhas.append((futuros[fut], str(erro)))
            if k % 100 == 0:
                f.flush()
                print(k, 'de', len(tarefas), 'falhas:', len(falhas), flush=True)
    print('fim; falhas:', falhas, flush=True)


if __name__ == '__main__':
    main()
