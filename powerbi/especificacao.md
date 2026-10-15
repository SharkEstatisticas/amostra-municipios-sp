# Painel de indicadores dos municípios de SP: especificação para o Power BI Desktop

Este documento diz o que montar, campo por campo, no Power BI Desktop. Quem o segue chega ao mesmo painel que a planilha `excel/amostra-municipios-sp.xlsx` mostra, com os mesmos números.

**O que ficou sem teste:** não há Power BI Desktop nesta máquina. As medidas DAX e as consultas Power Query abaixo foram escritas conferindo a sintaxe e a lógica contra os arquivos, mas **não foram executadas**. A tabela de conferência (`conferencia.md`) traz os números que cada medida tem de devolver; se um deles não bater, o defeito é da medida, e o valor certo está no SQLite.

Ordem para montar: 1) tema; 2) importar as consultas (§2); 3) relações (§3); 4) medidas (§4); 5) páginas (§5); 6) conferência (§7).

---

## 1. Para quem é e que decisão ele ajuda

Quem acompanha as contas e os serviços de um município (secretário de fazenda, de planejamento, controle interno, vereador, consultor) precisa saber, para um Indicador, três coisas: **onde o município está**, **onde estão os municípios parecidos** e **para onde a série aponta**. O painel responde só isso, com a definição escrita de cada Indicador à mão.

Tema: `tema-shark.json` (View → Themes → Browse for themes). As cores vêm de `identidade/cores.ts`: azul `#377EB8` para o município escolhido, cinza `#403A45` para o contexto (mediana e faixa dos parecidos), tinta `#0A0310` para texto, zebra `#F4F4F4` para fundo de bloco. Vermelho e verde ficam no tema só como cores de reserva do Power BI (funções "bom" e "ruim"); nenhum visual do painel os usa, porque nenhum Indicador desta amostra tem um lado "bom" e um "ruim" que valha para todo município.

## 2. Dados e consultas Power Query

Fonte: os CSV de `dados/tratados/` (UTF-8, vírgula como separador, ponto decimal). **Passo que costuma quebrar no Power BI em português:** o ponto decimal do CSV é lido como milhar se a configuração regional do Windows for pt-BR. Por isso toda conversão de tipo abaixo leva a cultura `"en-US"`.

Crie um parâmetro `PastaDados` (Texto) com o caminho da pasta `dados\tratados\` e uma consulta por arquivo:

```m
// dim_municipio
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_municipio.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cab = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cab, {{"cod_ibge", Int64.Type}, {"municipio", type text}, {"regiao_imediata", type text},
        {"regiao_intermediaria", type text}, {"populacao_censo_2022", Int64.Type}, {"faixa_porte", type text}}, "en-US")
in
    Tipos
```

```m
// dim_indicador
let
    Fonte = Csv.Document(File.Contents(PastaDados & "dim_indicador.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cab = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cab, {{"indicador_id", type text}, {"nome", type text}, {"unidade", type text},
        {"formula", type text}, {"fonte", type text}, {"periodicidade", type text}, {"meta", type text},
        {"sentido", type text}, {"casas", Int64.Type}, {"ordem", Int64.Type}}, "en-US")
in
    Tipos
```

```m
// fato_indicador  (indicadores_longo.csv)
let
    Fonte = Csv.Document(File.Contents(PastaDados & "indicadores_longo.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cab = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cab, {{"cod_ibge", Int64.Type}, {"municipio", type text}, {"faixa_porte", type text},
        {"ano", Int64.Type}, {"indicador_id", type text}, {"valor", type number}}, "en-US"),
    // o nome do município já está em dim_municipio: sai daqui para o modelo não ter a coluna duas vezes
    Enxuta = Table.RemoveColumns(Tipos, {"municipio"})
in
    Enxuta
```

```m
// ref_faixa  (referencia_faixa.csv): mediana e quartis dos municípios parecidos, por faixa, ano e indicador
let
    Fonte = Csv.Document(File.Contents(PastaDados & "referencia_faixa.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cab = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cab, {{"faixa_porte", type text}, {"ano", Int64.Type}, {"indicador_id", type text},
        {"n", Int64.Type}, {"minimo", type number}, {"maximo", type number}, {"media", type number},
        {"p25", type number}, {"mediana", type number}, {"p75", type number}}, "en-US")
in
    Tipos
```

```m
// previsao  (previsao_receita_total.csv)
let
    Fonte = Csv.Document(File.Contents(PastaDados & "previsao_receita_total.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cab = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cab, {{"cod_ibge", Int64.Type}, {"municipio", type text}, {"grupo_porte", type text},
        {"ano", Int64.Type}, {"metodo", type text}, {"previsto", type number}, {"inferior_80", type number},
        {"superior_80", type number}, {"inferior_95", type number}, {"superior_95", type number}}, "en-US"),
    Enxuta = Table.RemoveColumns(Tipos, {"municipio"})
in
    Enxuta
```

`backtest_metodos.csv` e `backtest_cobertura.csv` entram do mesmo jeito (consultas `backtest_metodos` e `backtest_cobertura`, colunas numéricas como `type number`), para a página 4.

Tabela de anos, em DAX (Modeling → New table). Vai até 2028 porque a previsão cobre 2026 a 2028:

```dax
dim_ano = SELECTCOLUMNS ( GENERATESERIES ( 2015, 2028, 1 ), "ano", [Value] )
```

Marque `dim_ano[ano]` como número inteiro, sem separador de milhar (Column tools → Format → Whole number, Thousands separator off), ou o eixo mostra "2.015".

## 3. Modelo de dados

Esquema em estrela, com `ref_faixa` solta de propósito.

| Tabela | Chave | Papel |
|---|---|---|
| `dim_municipio` | `cod_ibge` | uma linha por município (645), com a faixa de porte e a região |
| `dim_indicador` | `indicador_id` | uma linha por Indicador (8), com a definição escrita |
| `dim_ano` | `ano` | 2015 a 2028 |
| `fato_indicador` | (`cod_ibge`, `ano`, `indicador_id`) | valores, só onde a fonte tem dado |
| `previsao` | (`cod_ibge`, `ano`) | previsão da receita total, 2026 a 2028, com as faixas de 80% e 95% |
| `ref_faixa` | (`faixa_porte`, `ano`, `indicador_id`) | mediana e quartis dos municípios parecidos; **sem relação** |
| `backtest_metodos`, `backtest_cobertura` | | o teste do modelo; **sem relação** |

Relações (todas 1:N, direção única, do lado "um" para o lado "muitos"):

1. `dim_municipio[cod_ibge]` → `fato_indicador[cod_ibge]`
2. `dim_indicador[indicador_id]` → `fato_indicador[indicador_id]`
3. `dim_ano[ano]` → `fato_indicador[ano]`
4. `dim_municipio[cod_ibge]` → `previsao[cod_ibge]`
5. `dim_ano[ano]` → `previsao[ano]`

Por que `ref_faixa` fica solta: a chave dela é composta por três colunas, e o Power BI não relaciona por colunas compostas. As medidas filtram por `CALCULATE`, o que também evita a relação bidirecional (lenta e fácil de errar).

Configuração das colunas: `dim_municipio[municipio]` como "Data category: ... nenhuma"; esconda `fato_indicador[cod_ibge]`, `fato_indicador[ano]` e as chaves das dimensões (Hide in report view), para que o usuário use sempre as dimensões. `dim_indicador[nome]` classificada por `dim_indicador[ordem]` (Sort by column).

## 4. Medidas DAX

Crie uma tabela de medidas vazia (`Medidas`, Enter data com uma coluna) e ponha todas nela.

### 4.1 Base

```dax
Município selecionado =
SELECTEDVALUE ( dim_municipio[municipio], "Escolha um município" )

Indicador selecionado =
SELECTEDVALUE ( dim_indicador[nome], "Escolha um indicador" )

-- Em um município, um ano e um indicador há uma linha só; em qualquer outro nível é a média.
Valor =
AVERAGE ( fato_indicador[valor] )

Faixa de porte =
SELECTEDVALUE ( dim_municipio[faixa_porte] )

Municípios na faixa =
VAR faixa = SELECTEDVALUE ( dim_municipio[faixa_porte] )
RETURN
    IF (
        NOT ISBLANK ( faixa ),
        CALCULATE (
            DISTINCTCOUNT ( dim_municipio[cod_ibge] ),
            REMOVEFILTERS ( dim_municipio ),
            dim_municipio[faixa_porte] = faixa
        )
    )

Casas decimais =
SELECTEDVALUE ( dim_indicador[casas], 0 )

Valor formatado =
VAR v = [Valor]
RETURN
    IF ( ISBLANK ( v ), "sem dado", FORMAT ( v, IF ( [Casas decimais] = 0, "#,0", "#,0.0" ) ) )
```

### 4.2 O grupo de comparação (municípios parecidos)

Todas leem `ref_faixa` pela faixa do município escolhido, pelo ano do ponto do gráfico e pelo indicador do contexto. Sem município escolhido, devolvem vazio.

```dax
Mediana da faixa =
VAR faixa = SELECTEDVALUE ( dim_municipio[faixa_porte] )
VAR ano   = SELECTEDVALUE ( dim_ano[ano] )
VAR ind   = SELECTEDVALUE ( dim_indicador[indicador_id] )
RETURN
    IF (
        NOT ISBLANK ( faixa ) && NOT ISBLANK ( ano ) && NOT ISBLANK ( ind ),
        CALCULATE (
            MAX ( ref_faixa[mediana] ),
            ref_faixa[faixa_porte] = faixa,
            ref_faixa[ano] = ano,
            ref_faixa[indicador_id] = ind
        )
    )

1º quartil da faixa =
VAR faixa = SELECTEDVALUE ( dim_municipio[faixa_porte] )
VAR ano   = SELECTEDVALUE ( dim_ano[ano] )
VAR ind   = SELECTEDVALUE ( dim_indicador[indicador_id] )
RETURN
    IF (
        NOT ISBLANK ( faixa ) && NOT ISBLANK ( ano ) && NOT ISBLANK ( ind ),
        CALCULATE (
            MAX ( ref_faixa[p25] ),
            ref_faixa[faixa_porte] = faixa,
            ref_faixa[ano] = ano,
            ref_faixa[indicador_id] = ind
        )
    )

3º quartil da faixa =
VAR faixa = SELECTEDVALUE ( dim_municipio[faixa_porte] )
VAR ano   = SELECTEDVALUE ( dim_ano[ano] )
VAR ind   = SELECTEDVALUE ( dim_indicador[indicador_id] )
RETURN
    IF (
        NOT ISBLANK ( faixa ) && NOT ISBLANK ( ano ) && NOT ISBLANK ( ind ),
        CALCULATE (
            MAX ( ref_faixa[p75] ),
            ref_faixa[faixa_porte] = faixa,
            ref_faixa[ano] = ano,
            ref_faixa[indicador_id] = ind
        )
    )

Diferença para a mediana =
DIVIDE ( [Valor] - [Mediana da faixa], [Mediana da faixa] )
```

Formate `Diferença para a mediana` como porcentagem com uma casa.

```dax
-- 0 = menor valor da faixa naquele ano, 100% = maior. Mesma conta do PERCENT_RANK do SQL
-- (municípios com valor menor ÷ (n − 1)). É uma posição, e não uma nota.
Posição na faixa =
VAR v     = [Valor]
VAR faixa = SELECTEDVALUE ( dim_municipio[faixa_porte] )
VAR ano   = SELECTEDVALUE ( dim_ano[ano] )
VAR ind   = SELECTEDVALUE ( dim_indicador[indicador_id] )
VAR grupo =
    CALCULATETABLE (
        fato_indicador,
        REMOVEFILTERS ( dim_municipio ),
        REMOVEFILTERS ( dim_ano ),
        REMOVEFILTERS ( dim_indicador ),
        fato_indicador[faixa_porte] = faixa,
        fato_indicador[ano] = ano,
        fato_indicador[indicador_id] = ind
    )
VAR n        = COUNTROWS ( grupo )
VAR menores  = COUNTROWS ( FILTER ( grupo, fato_indicador[valor] < v ) )
RETURN
    IF ( NOT ISBLANK ( v ) && n > 1, DIVIDE ( menores, n - 1 ) )
```

### 4.3 Último valor e variação

```dax
Ano do último valor =
CALCULATE ( MAX ( fato_indicador[ano] ), REMOVEFILTERS ( dim_ano ) )

Último valor =
VAR a = [Ano do último valor]
RETURN
    CALCULATE ( [Valor], REMOVEFILTERS ( dim_ano ), fato_indicador[ano] = a )

Primeiro valor =
VAR a = CALCULATE ( MIN ( fato_indicador[ano] ), REMOVEFILTERS ( dim_ano ) )
RETURN
    CALCULATE ( [Valor], REMOVEFILTERS ( dim_ano ), fato_indicador[ano] = a )

Variação do período =
DIVIDE ( [Último valor] - [Primeiro valor], [Primeiro valor] )

Último valor da faixa =
VAR a     = [Ano do último valor]
VAR faixa = SELECTEDVALUE ( dim_municipio[faixa_porte] )
VAR ind   = SELECTEDVALUE ( dim_indicador[indicador_id] )
RETURN
    CALCULATE (
        MAX ( ref_faixa[mediana] ),
        ref_faixa[faixa_porte] = faixa,
        ref_faixa[ano] = a,
        ref_faixa[indicador_id] = ind
    )
```

`Último valor` e `Primeiro valor` só fazem sentido com um município e um indicador escolhidos; em uma tabela com vários indicadores, cada linha leva o seu próprio contexto e o resultado é correto por linha.

### 4.4 Previsão da receita (indicador `receita_total`)

```dax
Receita observada =
CALCULATE ( AVERAGE ( fato_indicador[valor] ), fato_indicador[indicador_id] = "receita_total" )

Receita prevista =
AVERAGE ( previsao[previsto] )

-- Ancora a linha tracejada no último ano observado (2025), para ela sair do ponto real.
Receita prevista (linha) =
VAR a = SELECTEDVALUE ( dim_ano[ano] )
RETURN
    IF ( a = 2025, [Receita observada], [Receita prevista] )

Limite inferior 80% =
VAR a = SELECTEDVALUE ( dim_ano[ano] )
RETURN IF ( a = 2025, [Receita observada], AVERAGE ( previsao[inferior_80] ) )

Limite superior 80% =
VAR a = SELECTEDVALUE ( dim_ano[ano] )
RETURN IF ( a = 2025, [Receita observada], AVERAGE ( previsao[superior_80] ) )

Limite inferior 95% =
VAR a = SELECTEDVALUE ( dim_ano[ano] )
RETURN IF ( a = 2025, [Receita observada], AVERAGE ( previsao[inferior_95] ) )

Limite superior 95% =
VAR a = SELECTEDVALUE ( dim_ano[ano] )
RETURN IF ( a = 2025, [Receita observada], AVERAGE ( previsao[superior_95] ) )

-- Para o cartão e a frase da página: o que se espera em 2028 e as duas faixas.
Receita prevista 2028 =
CALCULATE ( AVERAGE ( previsao[previsto] ), dim_ano[ano] = 2028 )

Texto da previsão =
VAR m   = [Município selecionado]
VAR p   = CALCULATE ( AVERAGE ( previsao[previsto] ),    dim_ano[ano] = 2028 )
VAR lo  = CALCULATE ( AVERAGE ( previsao[inferior_80] ), dim_ano[ano] = 2028 )
VAR hi  = CALCULATE ( AVERAGE ( previsao[superior_80] ), dim_ano[ano] = 2028 )
VAR lo9 = CALCULATE ( AVERAGE ( previsao[inferior_95] ), dim_ano[ano] = 2028 )
VAR hi9 = CALCULATE ( AVERAGE ( previsao[superior_95] ), dim_ano[ano] = 2028 )
RETURN
    IF (
        ISBLANK ( p ),
        "Este município não tem os cinco últimos anos de receita válidos: sem previsão.",
        "Em 2028, a receita corrente de " & m & " fica perto de R$ " & FORMAT ( p, "#,0" )
            & " milhões (a preços de 2025). Na faixa de 80% do teste do passado, entre R$ " & FORMAT ( lo, "#,0" )
            & " e R$ " & FORMAT ( hi, "#,0" ) & " milhões; na de 95%, entre R$ " & FORMAT ( lo9, "#,0" )
            & " e R$ " & FORMAT ( hi9, "#,0" ) & " milhões."
    )
```

A frase fala em "faixa do teste do passado", e não em "80% de chance": a faixa foi calibrada com os erros que o método cometeu, e na verificação com uma origem de fora ela cobriu, na média, o que prometeu, mas bem menos na origem 2022. A página 4 mostra os números; quem for ao ar com este painel deve manter o aviso da §5.3.

### 4.5 Títulos dinâmicos

```dax
Título da evolução =
[Indicador selecionado] & ": " & [Município selecionado] & " e a mediana de " & [Municípios na faixa]
    & " municípios da faixa " & LOWER ( MID ( [Faixa de porte], 4, 40 ) ) & " habitantes"
```

## 5. Páginas

Tamanho: 16:9 (1280 × 720). Fundo da página: branco. Blocos em cartão `#F4F4F4`. Título de página 20 pt, negrito, tinta. Texto de visual 10 a 12 pt. Fonte Segoe UI (padrão do Power BI) ou, se a identidade pedir, Lato.

### 5.1 Página "Município"

Pergunta: **onde este município está, e onde estão os parecidos?**

| Posição (x, y, l × a) | Visual | Campos | Formato |
|---|---|---|---|
| 24, 16, 540 × 40 | Caixa de texto | "Indicadores do município" | título |
| 24, 64, 320 × 56 | **Segmentação** (slicer), lista suspensa com busca, seleção única | `dim_municipio[municipio]` | Seleção única ligada; "Selecionar tudo" desligado. Estado inicial: um município |
| 360, 64, 260 × 56 | Cartão | `[Faixa de porte]` | rótulo "Municípios parecidos: faixa de porte" |
| 640, 64, 200 × 56 | Cartão | `[Municípios na faixa]` | rótulo "Municípios na faixa" |
| 860, 64, 200 × 56 | Cartão | `dim_municipio[populacao_censo_2022]` | agregação: Máximo; rótulo "População (Censo 2022)" |
| 24, 136, 1232 × 112 | **Linha de cartões** (4 cartões de 296 × 112) | para cada um dos Indicadores `receita_pc`, `saude_pc`, `educacao_pc`, `dependencia_transf`: `[Último valor]`; subtítulo `[Último valor da faixa]` ("mediana da faixa") | filtrar o cartão por `dim_indicador[indicador_id]`; valor 28 pt, azul `#377EB8`; legenda em tinta |
| 24, 264, 760 × 440 | **Gráfico de linhas** | Eixo X: `dim_ano[ano]`. Valores: `[Valor]`, `[Mediana da faixa]`, `[1º quartil da faixa]`, `[3º quartil da faixa]`. Filtro do visual: um indicador por vez via segmentação | `[Valor]` azul 2,5 pt com marcador; `[Mediana da faixa]` cinza `#403A45` 2 pt; quartis cinza claro 1 pt. Título: `[Título da evolução]`. Legenda embaixo |
| 800, 264, 456 × 160 | Segmentação (botões) | `dim_indicador[nome]` (os sete indicadores; filtrar `receita_total` para fora desta página) | seleção única; ordem por `ordem` |
| 800, 440, 456 × 264 | Tabela | `dim_ano[ano]`, `[Valor formatado]`, `[Mediana da faixa]`, `[Diferença para a mediana]`, `[Posição na faixa]` | linhas zebradas; "Diferença para a mediana" com formato `+0,0%;-0,0%` e **sem** cor de bom/ruim |

Regra de leitura (escrever numa caixa de texto fixa ao pé): "A faixa cinza vai do 1º ao 3º quartil dos municípios parecidos. Estar acima ou abaixo da mediana não é, por si, bom nem ruim."

### 5.2 Página "Comparação na faixa"

Pergunta: **o município está no meio ou na ponta do grupo?**

| Visual | Campos | Formato |
|---|---|---|
| Segmentações sincronizadas com a página 1: município, indicador (seleção única) e ano | | |
| **Gráfico de dispersão** (um ponto por município da faixa) | Detalhes: `dim_municipio[municipio]`; X: `[Valor]`; Y: nenhum, use `dim_municipio[populacao_censo_2022]` com escala logarítmica | Pontos cinza `#403A45` a 60% de opacidade; o município escolhido em azul por regra de formatação condicional (campo: `[Município selecionado]` = `dim_municipio[municipio]`) e maior |
| Cartão | `[Posição na faixa]` | formato 0%; rótulo "Posição na faixa (0% = menor valor, 100% = maior)" |
| Cartão | `[Mediana da faixa]` e `[Diferença para a mediana]` | |

O filtro do visual de dispersão: `fato_indicador[faixa_porte]` igual à faixa do município escolhido. Na prática, crie uma medida de filtro `Na faixa = IF ( SELECTEDVALUE ( dim_municipio[faixa_porte] ) = MAX ( fato_indicador[faixa_porte] ), 1, 0 )` e use "é 1" no filtro do visual; para isso a segmentação de município precisa **não** filtrar o visual (Edit interactions → desligar), de modo que a dispersão mostre todos os municípios da faixa.

Sem ranking por nome: o painel de amostra mostra a posição relativa e o grupo, e **não** uma lista dos "piores" ou "melhores" municípios.

### 5.3 Página "Previsão da receita"

Pergunta: **quanto de receita o município pode contar para os próximos três anos, e com que margem de erro?**

| Visual | Campos | Formato |
|---|---|---|
| Segmentação do município (sincronizada) | | |
| **Gráfico de linhas** | Eixo: `dim_ano[ano]` (2015 a 2028). Valores: `[Receita observada]`, `[Receita prevista (linha)]`, `[Limite inferior 80%]`, `[Limite superior 80%]`, `[Limite inferior 95%]`, `[Limite superior 95%]` | Observada: azul sólida, 2,5 pt, marcador. Prevista: azul tracejada. Faixa de 80%: azul 1 pt. Faixa de 95%: cinza 1 pt pontilhada. Eixo Y em R$ milhões, sem zero forçado |
| Cartão | `[Receita prevista 2028]` | "R$ milhões, 2028, a preços de 2025" |
| Caixa de texto dinâmica | `[Texto da previsão]` | 14 pt |
| Caixa de texto fixa (obrigatória) | texto do Aviso abaixo | 10 pt, em cartão `#F4F4F4` |

Aviso (copiar como está): "Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. Não leva em conta mudança de lei, de alíquota, de convênio nem de gestão. A faixa mostra o quanto o método errou ao prever o passado de municípios do mesmo porte, alargada até a cobertura do teste chegar ao nível prometido; a página 'Como ler' mostra quanto ela acertou em cada ano deixado de fora, e em 2022 a de 80% ficou abaixo do prometido. Este painel é uma amostra feita com dado público e foi revista por estatístico registrado no CONRE (sem nome)."

### 5.4 Página "Como ler, fontes e limites"

| Visual | Campos |
|---|---|
| Tabela | `dim_indicador[nome]`, `[unidade]`, `[formula]`, `[fonte]`, `[periodicidade]`, `[meta]` (os Indicadores definidos por escrito) |
| Gráfico de colunas agrupadas | `backtest_metodos[horizonte]` × `backtest_metodos[erro_medio_abs_pct]`, legenda `backtest_metodos[metodo]`; o método escolhido em azul, os outros em cinza |
| Gráfico de pontos | `backtest_cobertura`: X = `origem_fora`, Y = `cobertura_com_ajuste` e `cobertura_sem_ajuste` (média ponderada por `n_teste`; crie as duas medidas com `SUMX` ou deixe a agregação em "Média"), legenda `nivel` |
| Caixa de texto | Fontes e licenças (copiar de `README.md`, seção "Fontes e licenças") e os cuidados: degrau do Censo 2022 nas séries por habitante; Ideb bienal; municípios sem rede municipal ficam sem Ideb |

## 6. Acessibilidade e entrega

- Texto alternativo em todo visual (Format → General → Alt text), dizendo o que o visual responde.
- Ordem de tabulação: segmentação de município, segmentação de indicador, visual principal, cartões, tabela.
- Contraste: texto em tinta sobre branco ou zebra; o azul cheio só em marca (linha, ponto) e em número grande de 28 pt, nunca em texto pequeno (razão de contraste de 4,3:1 sobre branco e de 3,95:1 sobre a zebra: passa para texto grande, que pede 3:1, e não para texto corrido, que pede 4,5:1; para texto pequeno azul use `#3579B1`).
- Nada depende só da cor: município e mediana têm legenda e rótulo direto; a linha da mediana é mais fina e escura, a do município é azul com marcador.
- Atualização: os CSV vêm de `scripts/` (ver `README.md`). No ambiente do Cliente, o mesmo modelo lê a base do Cliente por SQL (a consulta do `fato_indicador` troca `Csv.Document` por `Sql.Database`); as medidas não mudam.

## 7. Conferência

Antes de dar o painel por pronto, confira os números de `conferencia.md` (valor, mediana da faixa e posição de três municípios, gerados do SQLite). Se `Valor`, `Mediana da faixa` e `Posição na faixa` baterem nos três, as medidas estão certas; o que sobra é formato.
