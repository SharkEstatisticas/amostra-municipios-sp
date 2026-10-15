-- 20_indicadores.sql
-- Cada Indicador sai de uma consulta abaixo, em formato longo: (cod_ibge, ano, indicador_id, valor).
-- Valor ausente não entra na tabela: município que não entregou a declaração, ano em que a fonte
-- não publica ou declaração com valor implausível (ver "Qualidade da declaração") fica sem linha.
-- Nenhum valor é imputado.

------------------------------------------------------------------------------------------------
-- Deflator: IPCA (número-índice, dez/1993 = 100), média dos 12 meses de cada ano.
-- Fator para levar um valor do ano A a preços de 2025 = índice médio de 2025 ÷ índice médio de A.
-- A despesa e a receita são fluxos do ano inteiro, por isso a média do ano, e não o índice de dezembro.
------------------------------------------------------------------------------------------------
CREATE TABLE deflator AS
SELECT
    CAST(substr(mes, 1, 4) AS INTEGER) AS ano,
    AVG(indice)                        AS indice_medio,
    COUNT(*)                           AS meses
FROM stg_ipca
GROUP BY 1;

CREATE VIEW v_fator_2025 AS
SELECT d.ano, (SELECT indice_medio FROM deflator WHERE ano = 2025) / d.indice_medio AS fator
FROM deflator d;

------------------------------------------------------------------------------------------------
-- População.
--   2015 a 2021 e 2024 a 2025: estimativa do IBGE (SIDRA 6579).
--   2022: Censo 2022 (SIDRA 9514).
--   2023: média entre o Censo 2022 e a estimativa de 2024. O IBGE não publicou estimativa para 2023
--         na tabela 6579, e a população que o Siconfi grava em 2023 é a mesma de 2022, de antes do
--         Censo (cerca de 6% acima dele na mediana), o que faria a série pular e voltar.
--         É a única população que não é publicada pelo IBGE; a coluna "origem" a marca.
-- AVISO: as estimativas de 2015 a 2021 partem do Censo 2010 e as de 2022 em diante, do Censo 2022.
-- A série por habitante tem, por isso, um degrau entre 2021 e 2022 em municípios cuja população o
-- Censo corrigiu. O degrau é do denominador; a série "receita_total" não o tem.
------------------------------------------------------------------------------------------------
CREATE VIEW v_populacao AS
SELECT cod_ibge, ano, populacao * 1.0 AS populacao, 'IBGE, estimativa (SIDRA 6579)' AS origem
FROM stg_populacao_estimada
WHERE populacao IS NOT NULL AND ano BETWEEN 2015 AND 2025
UNION ALL
SELECT cod_ibge, ano, populacao * 1.0, 'IBGE, Censo 2022 (SIDRA 9514)'
FROM stg_populacao_censo2022
WHERE populacao IS NOT NULL AND ano = 2022
UNION ALL
SELECT c.cod_ibge, 2023, (c.populacao + e.populacao) / 2.0, 'Média entre o Censo 2022 e a estimativa 2024 (IBGE não publicou 2023)'
FROM stg_populacao_censo2022 c
JOIN stg_populacao_estimada e ON e.cod_ibge = c.cod_ibge AND e.ano = 2024
WHERE c.populacao IS NOT NULL AND e.populacao IS NOT NULL;

------------------------------------------------------------------------------------------------
-- Qualidade da declaração.
-- A DCA é autodeclarada. Em alguns anos um município declarou um valor várias vezes menor que o
-- dele mesmo nos outros anos (declaração incompleta). Entrar assim na comparação distorce a
-- mediana da faixa e a previsão. A regra, igual para todos os municípios e campos:
--   1. valor zero ou negativo não é valor (uma prefeitura não tem despesa nula com saúde);
--   2. em reais de 2025, o valor de um ano menor que 1/4 ou maior que 4 vezes a média dos OUTROS
--      anos do mesmo município é tratado como declaração inconsistente.
-- Os campos são a receita corrente líquida de deduções, a despesa com saúde e a despesa com educação.
-- A receita bruta e a transferência da mesma declaração saem com a receita. O que sai fica listado
-- em exclusao_declaracao (exportada em dados/tratados/exclusoes_declaracao.csv).
-- Ao comparar com a média dos outros anos usamos o próprio município: um município de royalties
-- (Ilhabela) tem receita alta em todos os anos e por isso não é cortado, o que uma regra contra a
-- mediana da faixa cortaria.
------------------------------------------------------------------------------------------------
CREATE VIEW v_siconfi_real AS
SELECT
    s.ano, s.cod_ibge, s.entregou_ic, s.entregou_ie, s.rc_bruta, s.transf_correntes,
    CASE WHEN s.entregou_ic = 1 THEN
        (s.rc_bruta - ABS(COALESCE(s.ded_fundeb, 0)) - ABS(COALESCE(s.outras_ded, 0))) * f.fator
    END AS rc_liq_real,
    CASE WHEN s.entregou_ie = 1 THEN s.saude_empenhada    * f.fator END AS saude_real,
    CASE WHEN s.entregou_ie = 1 THEN s.educacao_empenhada * f.fator END AS educacao_real
FROM stg_siconfi s
JOIN v_fator_2025 f ON f.ano = s.ano;

CREATE TABLE siconfi_analise AS
WITH positivo AS (
    SELECT ano, cod_ibge, entregou_ic, entregou_ie, rc_bruta, transf_correntes,
           CASE WHEN rc_liq_real   > 0 THEN rc_liq_real   END AS rc_liq,
           CASE WHEN saude_real    > 0 THEN saude_real    END AS saude,
           CASE WHEN educacao_real > 0 THEN educacao_real END AS educacao
    FROM v_siconfi_real
),
outros AS (   -- média dos outros anos do mesmo município (deixa o ano de fora)
    SELECT p.*,
        (SUM(rc_liq)   OVER w - rc_liq)   / NULLIF(COUNT(rc_liq)   OVER w - 1, 0) AS rc_liq_outros,
        (SUM(saude)    OVER w - saude)    / NULLIF(COUNT(saude)    OVER w - 1, 0) AS saude_outros,
        (SUM(educacao) OVER w - educacao) / NULLIF(COUNT(educacao) OVER w - 1, 0) AS educacao_outros
    FROM positivo p
    WINDOW w AS (PARTITION BY cod_ibge)
)
SELECT
    ano, cod_ibge, entregou_ic, entregou_ie, rc_bruta, transf_correntes,
    rc_liq, saude, educacao, rc_liq_outros, saude_outros, educacao_outros,
    CASE WHEN rc_liq   IS NULL OR rc_liq   / rc_liq_outros   < 0.25 OR rc_liq   / rc_liq_outros   > 4 THEN NULL ELSE rc_liq   END AS rc_liq_ok,
    CASE WHEN saude    IS NULL OR saude    / saude_outros    < 0.25 OR saude    / saude_outros    > 4 THEN NULL ELSE saude    END AS saude_ok,
    CASE WHEN educacao IS NULL OR educacao / educacao_outros < 0.25 OR educacao / educacao_outros > 4 THEN NULL ELSE educacao END AS educacao_ok
FROM outros;

-- O que saiu e por quê. "Não declarou" (entregou = 0) não entra: não há valor para tirar.
CREATE TABLE exclusao_declaracao AS
SELECT s.cod_ibge, m.municipio, s.ano, 'receita_corrente_liquida' AS campo,
       s.rc_liq_real AS valor_real_2025, a.rc_liq_outros AS media_dos_outros_anos,
       CASE WHEN s.rc_liq_real <= 0 THEN 'valor zero ou negativo' ELSE 'fora de 1/4 a 4 vezes a média dos outros anos' END AS motivo
FROM v_siconfi_real s
JOIN siconfi_analise a ON a.cod_ibge = s.cod_ibge AND a.ano = s.ano
JOIN stg_municipio m ON m.cod_ibge = s.cod_ibge
WHERE s.entregou_ic = 1 AND a.rc_liq_ok IS NULL
UNION ALL
SELECT s.cod_ibge, m.municipio, s.ano, 'despesa_saude', s.saude_real, a.saude_outros,
       CASE WHEN s.saude_real <= 0 THEN 'valor zero ou negativo' ELSE 'fora de 1/4 a 4 vezes a média dos outros anos' END
FROM v_siconfi_real s
JOIN siconfi_analise a ON a.cod_ibge = s.cod_ibge AND a.ano = s.ano
JOIN stg_municipio m ON m.cod_ibge = s.cod_ibge
WHERE s.entregou_ie = 1 AND a.saude_ok IS NULL
UNION ALL
SELECT s.cod_ibge, m.municipio, s.ano, 'despesa_educacao', s.educacao_real, a.educacao_outros,
       CASE WHEN s.educacao_real <= 0 THEN 'valor zero ou negativo' ELSE 'fora de 1/4 a 4 vezes a média dos outros anos' END
FROM v_siconfi_real s
JOIN siconfi_analise a ON a.cod_ibge = s.cod_ibge AND a.ano = s.ano
JOIN stg_municipio m ON m.cod_ibge = s.cod_ibge
WHERE s.entregou_ie = 1 AND a.educacao_ok IS NULL;

------------------------------------------------------------------------------------------------
-- A tabela de fatos. Uma consulta por Indicador.
------------------------------------------------------------------------------------------------
CREATE TABLE fato_indicador (
    cod_ibge     INTEGER NOT NULL,
    ano          INTEGER NOT NULL,
    indicador_id TEXT    NOT NULL,
    valor        REAL    NOT NULL,
    PRIMARY KEY (cod_ibge, ano, indicador_id)
);

-- 1. Receita corrente por habitante (R$ de 2025)
INSERT INTO fato_indicador
SELECT a.cod_ibge, a.ano, 'receita_pc', a.rc_liq_ok / p.populacao
FROM siconfi_analise a
JOIN v_populacao p ON p.cod_ibge = a.cod_ibge AND p.ano = a.ano
WHERE a.rc_liq_ok IS NOT NULL AND p.populacao > 0;

-- 2. Dependência de transferências (% da receita corrente bruta), na declaração que passou na regra
INSERT INTO fato_indicador
SELECT cod_ibge, ano, 'dependencia_transf', 100.0 * transf_correntes / rc_bruta
FROM siconfi_analise
WHERE rc_liq_ok IS NOT NULL AND rc_bruta > 0 AND transf_correntes IS NOT NULL;

-- 3. Despesa com saúde por habitante (R$ de 2025)
INSERT INTO fato_indicador
SELECT a.cod_ibge, a.ano, 'saude_pc', a.saude_ok / p.populacao
FROM siconfi_analise a
JOIN v_populacao p ON p.cod_ibge = a.cod_ibge AND p.ano = a.ano
WHERE a.saude_ok IS NOT NULL AND p.populacao > 0;

-- 4. Despesa com educação por habitante (R$ de 2025)
INSERT INTO fato_indicador
SELECT a.cod_ibge, a.ano, 'educacao_pc', a.educacao_ok / p.populacao
FROM siconfi_analise a
JOIN v_populacao p ON p.cod_ibge = a.cod_ibge AND p.ano = a.ano
WHERE a.educacao_ok IS NOT NULL AND p.populacao > 0;

-- 5. PIB por habitante (R$ de 2025). O PIB vem em R$ mil, por isso o × 1000.
INSERT INTO fato_indicador
SELECT b.cod_ibge, b.ano, 'pib_pc', (b.pib_mil_reais * 1000.0 * f.fator) / p.populacao
FROM stg_pib b
JOIN v_fator_2025 f ON f.ano = b.ano
JOIN v_populacao p ON p.cod_ibge = b.cod_ibge AND p.ano = b.ano
WHERE b.pib_mil_reais IS NOT NULL AND p.populacao > 0 AND b.ano BETWEEN 2015 AND 2025;

-- 6. Ideb dos anos iniciais, rede municipal: o valor é o do INEP, sem conta nossa.
INSERT INTO fato_indicador
SELECT cod_ibge, ano, 'ideb', ideb
FROM stg_ideb
WHERE ideb IS NOT NULL;

-- 7. Nascidos de mães com 7 ou mais consultas de pré-natal (% dos nascidos com consulta informada).
--    O SINASC usa o código de 6 dígitos (sem o dígito verificador): casamos pelos 6 primeiros do IBGE.
--    Município com menos de 20 nascidos com a consulta informada no ano fica de fora: um percentual de
--    20 nascimentos varia em 5 pontos com um único caso e não diz nada sobre o serviço.
INSERT INTO fato_indicador
SELECT m.cod_ibge, n.ano, 'pre_natal_7mais', 100.0 * n.pre_natal_7mais / n.pre_natal_informado
FROM stg_sinasc n
JOIN stg_municipio m ON substr(CAST(m.cod_ibge AS TEXT), 1, 6) = n.cod_municipio6
WHERE n.pre_natal_informado >= 20;

-- 8. Receita corrente total (R$ milhões de 2025): a série que o modelo de previsão usa.
INSERT INTO fato_indicador
SELECT cod_ibge, ano, 'receita_total', rc_liq_ok / 1000000.0
FROM siconfi_analise
WHERE rc_liq_ok IS NOT NULL;
