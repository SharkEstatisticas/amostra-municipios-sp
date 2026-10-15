-- 30_referencia.sql
-- O que cada município é comparado: os municípios da mesma faixa de porte, no mesmo ano.
-- Mediana e quartis por faixa, ano e indicador, com interpolação linear (o padrão do NumPy:
-- posição = 1 + (n − 1) × p). O SQLite não tem MEDIAN nem PERCENTILE; esta consulta faz a conta.
-- O teste de scripts/validar.py confere cada número desta tabela contra o NumPy.

CREATE TABLE ref_faixa AS
WITH ordenado AS (
    SELECT
        d.faixa_porte,
        f.ano,
        f.indicador_id,
        f.valor,
        ROW_NUMBER() OVER (PARTITION BY d.faixa_porte, f.ano, f.indicador_id ORDER BY f.valor) AS r,
        COUNT(*)     OVER (PARTITION BY d.faixa_porte, f.ano, f.indicador_id)                  AS n
    FROM fato_indicador f
    JOIN dim_municipio d ON d.cod_ibge = f.cod_ibge
),
grupo AS (
    SELECT faixa_porte, ano, indicador_id, MAX(n) AS n,
           MIN(valor) AS minimo, MAX(valor) AS maximo, AVG(valor) AS media
    FROM ordenado
    GROUP BY faixa_porte, ano, indicador_id
),
posicao AS (   -- a posição fracionária de cada percentil dentro do grupo ordenado
    SELECT g.*, p.p, 1 + (g.n - 1) * p.p AS x
    FROM grupo g
    CROSS JOIN (SELECT 0.25 AS p UNION ALL SELECT 0.50 UNION ALL SELECT 0.75) p
),
percentil AS (
    SELECT
        q.faixa_porte, q.ano, q.indicador_id, q.p,
        lo.valor + (q.x - CAST(q.x AS INTEGER)) * (hi.valor - lo.valor) AS v
    FROM posicao q
    JOIN ordenado lo ON lo.faixa_porte = q.faixa_porte AND lo.ano = q.ano
                    AND lo.indicador_id = q.indicador_id AND lo.r = CAST(q.x AS INTEGER)
    JOIN ordenado hi ON hi.faixa_porte = q.faixa_porte AND hi.ano = q.ano
                    AND hi.indicador_id = q.indicador_id
                    AND hi.r = MIN(CAST(q.x AS INTEGER) + 1, q.n)
)
SELECT
    g.faixa_porte, g.ano, g.indicador_id, g.n, g.minimo, g.maximo, g.media,
    MAX(CASE WHEN pc.p = 0.25 THEN pc.v END) AS p25,
    MAX(CASE WHEN pc.p = 0.50 THEN pc.v END) AS mediana,
    MAX(CASE WHEN pc.p = 0.75 THEN pc.v END) AS p75
FROM grupo g
JOIN percentil pc ON pc.faixa_porte = g.faixa_porte AND pc.ano = g.ano AND pc.indicador_id = g.indicador_id
GROUP BY g.faixa_porte, g.ano, g.indicador_id, g.n, g.minimo, g.maximo, g.media;

-- A posição relativa de cada município no grupo: 0 = menor valor da faixa, 100 = maior.
-- É uma posição, e não uma nota: para a maior parte dos Indicadores, mais alto não é melhor.
CREATE VIEW v_posicao AS
SELECT
    f.cod_ibge, f.ano, f.indicador_id, f.valor, d.faixa_porte,
    100.0 * PERCENT_RANK() OVER (PARTITION BY d.faixa_porte, f.ano, f.indicador_id ORDER BY f.valor) AS posicao_na_faixa
FROM fato_indicador f
JOIN dim_municipio d ON d.cod_ibge = f.cod_ibge;
