-- 00_esquema.sql
-- Tabelas de entrada ("stg_" = staging): cada uma é o CSV de dados/brutos/ copiado sem mudar um valor.
-- O script scripts/construir_base.py cria estas tabelas, carrega os CSV e roda os arquivos .sql em ordem.

-- Municípios de SP e a região geográfica imediata (IBGE, API de Localidades).
CREATE TABLE stg_municipio (
    cod_ibge             INTEGER PRIMARY KEY,   -- código IBGE de 7 dígitos
    municipio            TEXT NOT NULL,
    regiao_imediata      TEXT,
    regiao_intermediaria TEXT
);

-- Declaração de Contas Anuais (Siconfi/Tesouro), um registro por município e ano.
CREATE TABLE stg_siconfi (
    ano                INTEGER NOT NULL,
    cod_ibge           INTEGER NOT NULL,
    entregou_ic        INTEGER NOT NULL,   -- 1 se o município entregou o Anexo I-C (receitas)
    entregou_ie        INTEGER NOT NULL,   -- 1 se entregou o Anexo I-E (despesas por função)
    populacao          INTEGER,            -- população que o Siconfi usa no ano (estimativa do IBGE)
    rc_bruta           REAL,               -- receitas correntes, brutas realizadas (R$ correntes)
    ded_fundeb         REAL,               -- dedução da receita para o Fundeb (R$ correntes)
    outras_ded         REAL,               -- outras deduções da receita (R$ correntes)
    transf_correntes   REAL,               -- transferências correntes, brutas realizadas (R$ correntes)
    saude_empenhada    REAL,               -- função 10 - Saúde, despesa empenhada (R$ correntes)
    educacao_empenhada REAL,               -- função 12 - Educação, despesa empenhada (R$ correntes)
    PRIMARY KEY (ano, cod_ibge)
);

-- População estimada pelo IBGE (SIDRA 6579) e Censo 2022 (SIDRA 9514).
CREATE TABLE stg_populacao_estimada (cod_ibge INTEGER, ano INTEGER, populacao INTEGER);
CREATE TABLE stg_populacao_censo2022 (cod_ibge INTEGER, ano INTEGER, populacao INTEGER);

-- PIB municipal a preços correntes, em R$ mil (IBGE, SIDRA 5938).
CREATE TABLE stg_pib (cod_ibge INTEGER, ano INTEGER, pib_mil_reais REAL);

-- IPCA, número-índice mensal (IBGE, SIDRA 1737): o deflator.
CREATE TABLE stg_ipca (mes TEXT, indice REAL);

-- Ideb, anos iniciais, rede municipal (INEP).
CREATE TABLE stg_ideb (cod_ibge INTEGER, ano INTEGER, ideb REAL);

-- Nascidos vivos por município de residência da mãe (SINASC/DataSUS), já contados por script.
CREATE TABLE stg_sinasc (
    ano                 INTEGER,
    cod_municipio6      TEXT,      -- código IBGE sem o dígito verificador (6 dígitos)
    nascidos            INTEGER,
    pre_natal_informado INTEGER,   -- nascidos com a consulta de pré-natal informada (exclui "ignorado")
    pre_natal_7mais     INTEGER,   -- nascidos de mães com 7 ou mais consultas de pré-natal
    parto_informado     INTEGER,
    parto_cesareo       INTEGER
);
