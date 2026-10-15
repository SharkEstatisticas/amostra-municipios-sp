-- 40_consultas_exemplo.sql
-- Consultas para perguntas que um secretário, um vereador ou um analista fazem. Rodam sobre
-- dados/tratados/amostra.sqlite (sqlite3 dados/tratados/amostra.sqlite < sql/40_consultas_exemplo.sql,
-- ou qualquer cliente SQLite). Troque o nome do município na cláusula WHERE.
--
-- Nenhuma delas ordena municípios do pior ao melhor: a amostra mostra posição e grupo, não ranking.

-- 1. Série de um município, ano a ano, com a mediana e os quartis da faixa dele, para um indicador.
SELECT
    f.ano,
    ROUND(f.valor, 1)    AS valor_municipio,
    ROUND(r.mediana, 1)  AS mediana_da_faixa,
    ROUND(r.p25, 1)      AS primeiro_quartil,
    ROUND(r.p75, 1)      AS terceiro_quartil,
    ROUND(100.0 * (f.valor / r.mediana - 1), 1) AS diferenca_para_mediana_pct
FROM fato_indicador f
JOIN dim_municipio d ON d.cod_ibge = f.cod_ibge
JOIN ref_faixa r     ON r.faixa_porte = d.faixa_porte AND r.ano = f.ano AND r.indicador_id = f.indicador_id
WHERE d.municipio = 'Rio Claro'
  AND f.indicador_id = 'saude_pc'
ORDER BY f.ano;

-- 2. Onde o município está na faixa em 2024, em todos os indicadores: posição de 0 a 100.
SELECT i.nome, ROUND(p.valor, 1) AS valor, ROUND(p.posicao_na_faixa) AS posicao_0_a_100
FROM v_posicao p
JOIN dim_municipio d ON d.cod_ibge = p.cod_ibge
JOIN dim_indicador i ON i.indicador_id = p.indicador_id
WHERE d.municipio = 'Rio Claro' AND p.ano = 2024
ORDER BY i.ordem;

-- 3. Quantos municípios da faixa de um município declararam e entraram na comparação, por indicador (2024).
SELECT r.indicador_id, r.n AS municipios_com_dado, (SELECT COUNT(*) FROM dim_municipio d2 WHERE d2.faixa_porte = r.faixa_porte) AS municipios_na_faixa
FROM ref_faixa r
WHERE r.ano = 2024
  AND r.faixa_porte = (SELECT faixa_porte FROM dim_municipio WHERE municipio = 'Rio Claro')
ORDER BY r.indicador_id;

-- 4. Previsão de receita do município, com as duas faixas de incerteza.
SELECT ano,
       ROUND(previsto, 1)     AS previsto_milhoes_de_2025,
       ROUND(inferior_80, 1)  AS inferior_80,
       ROUND(superior_80, 1)  AS superior_80,
       ROUND(inferior_95, 1)  AS inferior_95,
       ROUND(superior_95, 1)  AS superior_95
FROM previsao_receita_total
WHERE municipio = 'Rio Claro'
ORDER BY ano;

-- 5. Dependência de transferências por faixa de porte, em 2025: a mediana de cada grupo.
SELECT faixa_porte, n AS municipios, ROUND(mediana, 1) AS mediana_pct, ROUND(p25, 1) AS p25, ROUND(p75, 1) AS p75
FROM ref_faixa
WHERE indicador_id = 'dependencia_transf' AND ano = 2025
ORDER BY faixa_porte;

-- 6. Municípios sem receita válida em um ano, por não ter declarado ao Tesouro ou por a declaração
--    ter sido excluída pela regra de qualidade (o que fica "n.d." na planilha). Em 2025, ano mais recente.
SELECT d.municipio, d.faixa_porte
FROM dim_municipio d
WHERE NOT EXISTS (
    SELECT 1 FROM fato_indicador f
    WHERE f.cod_ibge = d.cod_ibge AND f.ano = 2025 AND f.indicador_id = 'receita_pc')
ORDER BY d.municipio;

-- 7. O que a regra de qualidade tirou, e por quê (declarações incompletas do próprio município).
SELECT municipio, ano, campo, ROUND(valor_real_2025 / 1e6, 2) AS valor_milhoes, ROUND(media_dos_outros_anos / 1e6, 2) AS media_outros_anos_milhoes, motivo
FROM exclusao_declaracao
ORDER BY municipio, ano, campo;
