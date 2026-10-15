# Indicadores dos municípios de São Paulo: Entregável de amostra de Dados e indicadores

Feito com dado público, sem Cliente. Nenhum número aqui é resultado de Cliente, e nenhum dado pessoal entra: tudo é agregado por município.

> **Sobre a revisão.** A Revisão técnica por estatístico registrado no CONRE faz parte do processo de todo Projeto da Shark Estatística. Para esta amostra, feita só com dado público, ela ainda não está registrada neste repositório.

## 1. O problema

Quem acompanha as contas e os serviços de uma prefeitura tem o dado, mas não tem como responder, sem uma semana de planilha, a três perguntas simples: **onde o meu município está**, **onde estão os que se parecem com ele** e **para onde a série aponta**. O dado existe, aberto, em quatro lugares diferentes (Tesouro, IBGE, INEP, DataSUS), em formatos diferentes, com anos diferentes e com erros de declaração. Cada área do órgão chega com um número, e ninguém escreveu o que cada Indicador mede.

## 2. A solução

Uma base tratada para os 645 municípios de SP, de 2015 a 2025, com oito Indicadores definidos por escrito; consultas SQL que refazem cada um; uma planilha que alguém de fora abre e entende; a especificação de um painel de Power BI; e uma previsão simples da receita, com a incerteza à vista e testada contra o passado.

| Entrega | Onde está | Para quê |
|---|---|---|
| Base tratada | `dados/tratados/*.csv` e `dados/tratados/amostra.sqlite` | os números, em CSV (qualquer ferramenta) e em SQLite |
| Consultas SQL comentadas | `sql/` | refazem cada Indicador a partir do dado bruto |
| Planilha | `excel/amostra-municipios-sp.xlsx` | escolher o município e ler tabela, gráficos e previsão |
| Especificação do Power BI | `powerbi/` | modelo de dados, consultas, medidas DAX, páginas, tema e números de conferência |
| Modelo de previsão | `scripts/modelo.py`, `dados/tratados/backtest_*.csv` | previsão da receita de 2026 a 2028 e o teste contra o passado |
| Gráficos | `graficos/` | cores da identidade da Shark Estatística |

## 3. Os oito Indicadores

Cada um tem fórmula, fonte, periodicidade e meta escritas em `dados/tratados/dim_indicador.csv` (e na aba "Indicadores" da planilha). Valores em reais de 2025 (IPCA, média do ano).

| Indicador | Fonte | Anos |
|---|---|---|
| Receita corrente por habitante | Siconfi (DCA I-C), IBGE | 2015 a 2025 |
| Dependência de transferências (%) | Siconfi (DCA I-C) | 2015 a 2025 |
| Despesa com saúde por habitante | Siconfi (DCA I-E), IBGE | 2015 a 2025 |
| Despesa com educação por habitante | Siconfi (DCA I-E), IBGE | 2015 a 2025 |
| PIB por habitante | IBGE (PIB dos Municípios), IBGE | 2015 a 2023 |
| Ideb, anos iniciais, rede municipal | INEP | 2015, 2017, 2019, 2021, 2023 |
| Nascidos de mães com 7 ou mais consultas de pré-natal (%) | DataSUS (SINASC) | 2015 a 2024 |
| Receita corrente total (R$ milhões) | Siconfi (DCA I-C) | 2015 a 2025 |

"Municípios parecidos" são os da mesma faixa de população do Censo 2022 (sete faixas; ver `sql/10_dimensoes.sql`). A comparação mostra mediana, quartis e posição, e **nunca** um ranking por nome.

## 4. Como refazer

Precisa de Python 3.12 ou mais novo e de internet. A coleta do Siconfi leva de 1 a 3 horas, porque a API do Tesouro limita a taxa de pedidos; o resto leva minutos.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt        # Linux/macOS: .venv/bin/pip

# 1. coleta (cada script grava em dados/brutos/ e retoma de onde parou)
.venv/Scripts/python scripts/coletar_sidra.py        # população, PIB, IPCA (IBGE)
.venv/Scripts/python scripts/coletar_ideb.py         # Ideb (INEP)
.venv/Scripts/python scripts/coletar_sinasc.py 2015 2024   # nascidos vivos (DataSUS)
.venv/Scripts/python scripts/coletar_siconfi_ibge.py 2015 2025   # finanças (Tesouro) e lista de municípios (IBGE)

# 2. tratamento, modelo, conferências, gráficos e planilha
.venv/Scripts/python scripts/construir_base.py       # SQLite + CSV tratados, pelos arquivos de sql/
.venv/Scripts/python scripts/modelo.py               # previsão e teste contra o passado
.venv/Scripts/python scripts/validar.py              # refaz cada indicador em pandas e compara com o SQL
.venv/Scripts/python scripts/graficos.py
.venv/Scripts/python scripts/planilha.py
.venv/Scripts/python scripts/verificar_planilha.py "Santos"   # recalcula as fórmulas com outro motor
.venv/Scripts/python scripts/gerar_conferencia.py    # números de conferência do Power BI
```

Os arquivos brutos baixados (`.dbc` do DataSUS e a planilha do INEP, 300 MB) ficam fora do git; os CSV pequenos de `dados/brutos/` entram, para quem quiser conferir sem baixar tudo de novo.

## 5. Como refazer cada número

O caminho de um número é sempre o mesmo: **fonte bruta** → `dados/brutos/*.csv` (um por coleta) → **consulta SQL** em `sql/20_indicadores.sql` → `dados/tratados/indicadores_longo.csv` → **célula** da aba "Dados" da planilha → **medida DAX** do Power BI.

| Indicador | Bloco do SQL (`20_indicadores.sql`) | Coluna da aba "Dados" | Medida DAX |
|---|---|---|---|
| Receita corrente por habitante | "1. Receita corrente por habitante" | F | `[Valor]` com `receita_pc` |
| Dependência de transferências | "2." | G | `[Valor]` com `dependencia_transf` |
| Despesa com saúde por habitante | "3." | H | `[Valor]` com `saude_pc` |
| Despesa com educação por habitante | "4." | I | `[Valor]` com `educacao_pc` |
| PIB por habitante | "5." | J | `[Valor]` com `pib_pc` |
| Ideb | "6." | K | `[Valor]` com `ideb` |
| Pré-natal com 7 ou mais consultas | "7." | L | `[Valor]` com `pre_natal_7mais` |
| Receita corrente total | "8." | M | `[Receita observada]` |
| Mediana e quartis da faixa | `30_referencia.sql` | aba "Referência" | `[Mediana da faixa]`, `[1º quartil da faixa]`, `[3º quartil da faixa]` |
| Previsão | `scripts/modelo.py` | aba "Previsões" | `[Receita prevista]` |

### Um número, na mão

Receita corrente por habitante de **Ibirá**, 2024 (o município de exemplo dos gráficos, sorteado com semente fixa):

1. Dado bruto, `dados/brutos/siconfi_municipio_ano.csv`, linha de 2024 do município 3519402: receitas correntes brutas R$ 76.695.824,42; dedução do Fundeb R$ 7.370.859,96; outras deduções R$ 0,00.
2. Receita líquida: 76.695.824,42 − 7.370.859,96 − 0,00 = R$ 69.324.964,46.
3. Deflator: IPCA médio de 2025 (7.300,84) ÷ IPCA médio de 2024 (6.952,07) = 1,05017.
4. A preços de 2025: 69.324.964,46 × 1,05017 = R$ 72.802.772.
5. População de 2024 (IBGE, estimativa): 11.934 habitantes.
6. 72.802.772 ÷ 11.934 = **R$ 6.100,45 por habitante**, o valor que a consulta SQL grava e a planilha mostra.

A mediana dos 120 municípios da faixa "de 10 a 20 mil" em 2024 é R$ 6.454,15; Ibirá está 5,5% abaixo, na posição 0,38 da faixa (45 dos 119 outros municípios têm valor menor; 45 ÷ 119 = 0,378).

## 6. A previsão, em linguagem simples

**O que prevê:** a receita corrente de cada município em 2026, 2027 e 2028, em R$ milhões de 2025. Foi escolhida a receita total e não a por habitante porque a população tem um degrau em 2022 (Censo), que a receita total não tem.

**Como:** três métodos simples concorreram, todos usando só a série do próprio município: repetir o último valor, estender a tendência dos 3 últimos anos, ou estender uma reta ajustada aos 5 últimos. Cada um foi testado prevendo o passado (a previsão parte de 2019, 2020, 2021 e 2022 e é comparada ao que veio depois).

| Método | Erro médio, 1 ano à frente | 2 anos | 3 anos | Viés a 3 anos |
|---|---|---|---|---|
| Repetir o último valor | 7,0% | 12,7% | 18,4% | +18,2% |
| **Tendência dos 3 últimos anos (escolhido)** | **6,6%** | **9,4%** | **12,5%** | **+5,2%** |
| Reta dos 5 últimos anos | 6,8% | 10,0% | 13,3% | +9,1% |

Repetir o último valor erra por baixo porque a receita real cresceu no período; a tendência corrige isso.

**A incerteza:** as faixas de 80% e de 95% não saem de uma fórmula de erro normal: saem dos erros que o método de fato cometeu ao prever o passado, por horizonte e por grupo de porte. O ponto delicado é que a receita dos municípios se move junta (inflação, ICMS, transferências), então os quatro anos de origem do teste são, na prática, quatro "choques", e não centenas de observações independentes. Por isso a faixa foi testada **deixando uma origem de fora**: calibra com três anos e confere no quarto, repetido para os quatro.

| Faixa prometida | Cobertura no teste, sem ajuste | Fator de alargamento | Cobertura depois do ajuste | Pior origem deixada de fora, depois do ajuste |
|---|---|---|---|---|
| 80% | 71% | 1,25 | 81% | 62% (origem 2022) |
| 95% | 92% | 1,15 | 95% | 91% (origem 2022) |

**O que isso quer dizer, sem enfeite:** na média a faixa cobre o que promete, mas na origem de 2022, que vem depois de um salto de receita, a faixa de 80% cobriu só 62%. Com quatro origens, o ajuste é grosseiro. Use a faixa de 95% como a leitura prudente. O modelo não conhece mudança de lei, de convênio nem de gestão.

Gráficos: `graficos/03-previsao.png` (um município) e `graficos/04-teste-do-modelo.png` (os métodos e a cobertura).

## 7. Qualidade do dado: o que saiu e por quê

A DCA é autodeclarada, e alguns municípios declararam, em certos anos, valores várias vezes menores que os próprios dos outros anos. A regra, igual para todos: valor zero ou negativo sai; em reais de 2025, valor de um ano menor que 1/4 ou maior que 4 vezes a média dos **outros** anos do mesmo município sai. A regra compara o município com ele mesmo, e não com a faixa: um município de royalties (Ilhabela) tem receita alta em todos os anos e fica. Saíram 27 valores de 15 municípios, de 7.095 declarações, todos listados em `dados/tratados/exclusoes_declaracao.csv`. Fora isso, município que não entregou a declaração fica sem valor, e nada foi imputado.

Conferências em `scripts/validar.py` (relatório em `dados/tratados/validacao.txt`): cada Indicador refeito em pandas, sem olhar o SQL, bate com o SQL linha a linha (diferença máxima zero); os quartis por faixa batem com o NumPy; a população do Siconfi bate com a do IBGE em 2015 a 2021 (mediana de diferença 0,77%).

## 8. Fontes e licenças

Consulta feita em 14/10/2026. "Lido" quer dizer que o texto foi lido nesse dia; onde não consegui ler o texto de licença, está dito.

| Base | Órgão | Condição de uso encontrada | Situação |
|---|---|---|---|
| DCA, anexos I-C e I-E (Siconfi) | Tesouro Nacional | A página de APIs diz que os dados são "disponibilizados para livre utilização" ([gov.br/tesouronacional, APIs](https://www.gov.br/tesouronacional/pt-br/central-de-conteudo/apis)). Sem instrução de citação | Lido. Texto formal de licença da base: não encontrado |
| População (SIDRA 6579 e 9514), PIB dos Municípios (5938), IPCA (1737), Localidades | IBGE | Dado aberto de órgão federal, sob o Decreto 8.777/2016: "licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte" ([Decreto 8.777/2016, art. 2º, III](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm)) | As páginas de termos do IBGE bloqueiam acesso automatizado (HTTP 403): **o texto próprio do IBGE não foi lido** |
| Ideb, anos iniciais, por município (divulgação 2023) | INEP | A Portaria Inep nº 380/2020 define dados abertos como os "sob licença aberta [...] limitando-se a creditar sua autoria ou a fonte" ([Política e Plano de Dados Abertos do Inep](https://download.inep.gov.br/publicacoes/institucionais/gestao_e_governanca/politica_e_plano_de_dados_abertos.pdf)). O CC BY 4.0 como licença padrão aparece em fonte secundária (Portaria nº 496/2021) | Portaria 380 lida; **Portaria 496 não lida em fonte primária** |
| SINASC, arquivos DNSP 2015 a 2024 | Ministério da Saúde (DataSUS) | "Os dados estão disponíveis de forma pública e anonimizada" ([gov.br/saude, natalidade](https://www.gov.br/saude/pt-br/acesso-a-informacao/sic/dados-em-transparencia-ativa/svsa/natalidade)); o rodapé dos sites do Ministério traz CC BY-ND 3.0 para o conteúdo do site, não declarado para os arquivos de dados | Lido. Licença do arquivo de microdados: não está escrita no FTP |

Condição comum a todas: **creditar a fonte**. Cada gráfico e a aba "Fontes e licenças" da planilha o fazem. Esta seção não é parecer jurídico: **validar com advogado** a redação da atribuição antes de publicar fora da Shark (pendência registrada).

## 9. Limites e cuidados

- **Degrau do Censo.** A população de 2015 a 2021 projeta o Censo 2010 e a de 2022 em diante vem do Censo 2022. Os quatro Indicadores por habitante saltam entre 2021 e 2022 em municípios que o Censo corrigiu. A série de receita total não tem o degrau.
- **População de 2023.** O IBGE não publicou estimativa para 2023 na tabela usada, e a população que o Siconfi grava em 2022 e em 2023 é a de antes do Censo (6% acima, na mediana). Usei a média entre o Censo 2022 e a estimativa de 2024, marcada na coluna `origem` de `populacao.csv`. É a única população que não é publicada pelo IBGE.
- **Ideb** é bienal, e município sem rede municipal fica sem Ideb. **PIB municipal** termina em 2023. **Pré-natal:** município com menos de 20 nascidos com consulta informada no ano fica de fora.
- **Municípios parecidos** é só porte. Dois municípios do mesmo porte podem ser muito diferentes (turismo, indústria, região metropolitana).
- **O Power BI não foi montado nem executado.** Não há Power BI Desktop nesta máquina. A especificação e as medidas DAX estão escritas, e a tabela `powerbi/conferencia.md` traz o que cada medida tem de devolver.
- **A planilha foi conferida com um motor de fórmulas independente** (`formulas`, em Python), não com o Excel: 869 fórmulas recalculadas, nenhuma divergência do valor gravado. O arquivo não foi aberto no Excel nesta máquina (não há Excel nem LibreOffice).
- **Os gráficos da planilha** usam `#N/D` de propósito, nas linhas de apoio, para interromper a linha onde não há dado.


## 10. Estrutura

```
/
  README.md  requirements.txt
  scripts/    coleta (4), construir_base, modelo, validar, graficos, planilha, verificar_planilha, gerar_conferencia, dbc, comum
  sql/        00_esquema, 10_dimensoes, 20_indicadores, 30_referencia, 40_consultas_exemplo
  dados/brutos/     CSV de cada coleta (os .dbc e .xlsx baixados ficam fora do git)
  dados/tratados/   CSV finais, amostra.sqlite, validacao.txt, exclusoes_declaracao.csv, backtest_*.csv, previsao_receita_total.csv
  excel/      amostra-municipios-sp.xlsx
  powerbi/    especificacao.md, conferencia.md, tema-shark.json
  graficos/   01 a 04 (.png)
```
