-- 10_dimensoes.sql
-- As dimensões do modelo: município (com a faixa de porte), ano e indicador (com a definição escrita).

-- Faixa de porte: o que esta amostra chama de "municípios parecidos".
-- A régua é a população do Censo 2022 (SIDRA 9514), igual para todos os anos, para que um município
-- não troque de grupo de um ano para o outro. Os cortes separam o que muda de natureza: a prefeitura
-- de 5 mil habitantes e a de 500 mil não são o mesmo tipo de órgão.
CREATE TABLE dim_municipio AS
SELECT
    m.cod_ibge,
    m.municipio,
    m.regiao_imediata,
    m.regiao_intermediaria,
    c.populacao AS populacao_censo_2022,
    CASE
        WHEN c.populacao <=   5000 THEN '1. Até 5 mil'
        WHEN c.populacao <=  10000 THEN '2. De 5 a 10 mil'
        WHEN c.populacao <=  20000 THEN '3. De 10 a 20 mil'
        WHEN c.populacao <=  50000 THEN '4. De 20 a 50 mil'
        WHEN c.populacao <= 100000 THEN '5. De 50 a 100 mil'
        WHEN c.populacao <= 500000 THEN '6. De 100 a 500 mil'
        ELSE                            '7. Mais de 500 mil'
    END AS faixa_porte
FROM stg_municipio m
JOIN stg_populacao_censo2022 c ON c.cod_ibge = m.cod_ibge;

CREATE TABLE dim_ano (ano INTEGER PRIMARY KEY);
INSERT INTO dim_ano VALUES (2015),(2016),(2017),(2018),(2019),(2020),(2021),(2022),(2023),(2024),(2025);

-- Cada Indicador definido por escrito: fórmula, fonte, periodicidade e meta (CONTEXT.md).
-- "sentido" é uma leitura de apoio, não um juízo de gestão: "neutro" quer dizer que mais ou menos
-- depende da escolha do município, e não de acerto ou erro.
CREATE TABLE dim_indicador (
    indicador_id   TEXT PRIMARY KEY,
    nome           TEXT NOT NULL,
    unidade        TEXT NOT NULL,
    formula        TEXT NOT NULL,
    fonte          TEXT NOT NULL,
    periodicidade  TEXT NOT NULL,
    meta           TEXT NOT NULL,
    sentido        TEXT NOT NULL,
    casas          INTEGER NOT NULL,   -- casas decimais ao exibir
    ordem          INTEGER NOT NULL
);

INSERT INTO dim_indicador VALUES
('receita_pc', 'Receita corrente por habitante', 'R$ por habitante, a preços de 2025',
 '(receitas correntes brutas realizadas − dedução do Fundeb − outras deduções) ÷ população, deflacionado pelo IPCA para a média de 2025',
 'Siconfi/Tesouro Nacional, DCA Anexo I-C; população do mesmo registro (IBGE); IPCA do IBGE (SIDRA 1737)',
 'Anual', 'Sem meta nesta amostra: o município a define na lei orçamentária', 'neutro', 0, 1),
('dependencia_transf', 'Dependência de transferências', '% da receita corrente',
 'transferências correntes brutas realizadas ÷ receitas correntes brutas realizadas × 100',
 'Siconfi/Tesouro Nacional, DCA Anexo I-C',
 'Anual', 'Sem meta nesta amostra', 'neutro', 1, 2),
('saude_pc', 'Despesa com saúde por habitante', 'R$ por habitante, a preços de 2025',
 'despesa empenhada na função 10 (Saúde) ÷ população, deflacionada pelo IPCA para a média de 2025',
 'Siconfi/Tesouro Nacional, DCA Anexo I-E; população do mesmo registro (IBGE); IPCA do IBGE',
 'Anual', 'Sem meta nesta amostra (o piso constitucional é medido sobre a receita de impostos, outro indicador)', 'neutro', 0, 3),
('educacao_pc', 'Despesa com educação por habitante', 'R$ por habitante, a preços de 2025',
 'despesa empenhada na função 12 (Educação) ÷ população, deflacionada pelo IPCA para a média de 2025',
 'Siconfi/Tesouro Nacional, DCA Anexo I-E; população do mesmo registro (IBGE); IPCA do IBGE',
 'Anual', 'Sem meta nesta amostra (o piso constitucional é medido sobre a receita de impostos, outro indicador)', 'neutro', 0, 4),
('pib_pc', 'PIB por habitante', 'R$ por habitante, a preços de 2025',
 'PIB municipal a preços correntes × 1.000 ÷ população, deflacionado pelo IPCA para a média de 2025',
 'IBGE, Produto Interno Bruto dos Municípios (SIDRA 5938); população do Siconfi (IBGE); IPCA do IBGE',
 'Anual, com defasagem de dois anos (último ano publicado: 2023)', 'Sem meta', 'maior', 0, 5),
('ideb', 'Ideb dos anos iniciais, rede municipal', 'nota de 0 a 10',
 'Ideb observado (fluxo escolar × desempenho no Saeb), 1º ao 5º ano, escolas da rede municipal',
 'INEP, Ideb 2023, divulgação por município',
 'Bienal (2015, 2017, 2019, 2021, 2023)', 'A meta do Ideb é do INEP e vai até 2021; não entra nesta amostra', 'maior', 1, 6),
('pre_natal_7mais', 'Nascidos de mães com 7 ou mais consultas de pré-natal', '% dos nascidos vivos com número de consultas informado',
 'nascidos vivos de mães com 7 ou mais consultas de pré-natal ÷ nascidos vivos com o número de consultas informado × 100, pelo município de residência da mãe',
 'SINASC/DataSUS, Declaração de Nascido Vivo (arquivos DNSP, ano de nascimento)',
 'Anual', 'Sem meta nesta amostra', 'maior', 1, 7),
('receita_total', 'Receita corrente total', 'R$ milhões, a preços de 2025',
 'receitas correntes brutas realizadas − dedução do Fundeb − outras deduções, deflacionado pelo IPCA para a média de 2025',
 'Siconfi/Tesouro Nacional, DCA Anexo I-C; IPCA do IBGE (SIDRA 1737)',
 'Anual', 'Sem meta nesta amostra. É a série que o modelo de previsão usa, porque não depende da população', 'neutro', 1, 8);
