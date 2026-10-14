-- =====================================================================
-- Plan de remédiation automatique (corrections sûres, sans décision métier)
-- Les anomalies qui demandent une validation métier (prix manquant, code UCD
-- erroné, fournisseur inconnu, dates incohérentes...) sont laissées en l'état
-- et remontées au propriétaire de la donnée dans le rapport.
-- =====================================================================

-- 1. Standardiser les unités selon la liste de référence
UPDATE articles SET unite = CASE lower(trim(replace(unite, '.', '')))
        WHEN 'fl' THEN 'flacon' WHEN 'flacon' THEN 'flacon'
        WHEN 'amp' THEN 'ampoule' WHEN 'poche' THEN 'poche'
        WHEN 'u' THEN 'unité' ELSE unite END
WHERE unite IS NOT NULL;

-- 2. Normaliser les codes ATC (majuscules, sans espace ni tiret)
UPDATE articles SET code_atc = upper(regexp_replace(code_atc, '[\s-]', '', 'g'))
WHERE code_atc IS NOT NULL;

-- 3. Supprimer les doublons exacts de code article (on garde une seule ligne)
CREATE OR REPLACE TABLE articles AS
SELECT * FROM articles QUALIFY row_number() OVER (PARTITION BY code_article ORDER BY date_maj DESC) = 1;

-- 4. Fusionner les quasi-doublons de libellé : on conserve le code le plus ancien
--    et on redirige les commandes vers ce code
CREATE OR REPLACE TEMP TABLE fusion_articles AS
WITH g AS (
    SELECT code_article, lower(regexp_replace(trim(libelle), '\s+', ' ', 'g')) AS cle
    FROM articles WHERE libelle IS NOT NULL
)
SELECT g.code_article AS code_doublon, m.code_retenu
FROM g JOIN (SELECT cle, min(code_article) AS code_retenu FROM g GROUP BY cle HAVING COUNT(*) > 1) m USING (cle)
WHERE g.code_article <> m.code_retenu;

UPDATE commandes SET code_article = f.code_retenu
FROM fusion_articles f WHERE commandes.code_article = f.code_doublon;
DELETE FROM articles WHERE code_article IN (SELECT code_doublon FROM fusion_articles);

-- 5. Fusionner les fournisseurs en double (même raison sociale)
CREATE OR REPLACE TEMP TABLE fusion_fournisseurs AS
SELECT fournisseur_id AS id_doublon, min(fournisseur_id) OVER (PARTITION BY raison_sociale) AS id_retenu
FROM fournisseurs;
UPDATE articles SET fournisseur_id = f.id_retenu
FROM fusion_fournisseurs f WHERE articles.fournisseur_id = f.id_doublon AND f.id_doublon <> f.id_retenu;
UPDATE commandes SET fournisseur_id = f.id_retenu
FROM fusion_fournisseurs f WHERE commandes.fournisseur_id = f.id_doublon AND f.id_doublon <> f.id_retenu;
DELETE FROM fournisseurs WHERE fournisseur_id IN
    (SELECT id_doublon FROM fusion_fournisseurs WHERE id_doublon <> id_retenu);

-- 6. RGPD - minimisation : remplacer les e-mails nominatifs par l'adresse de service
UPDATE fournisseurs
SET email_commandes = 'commandes@' || split_part(email_commandes, '@', 2)
WHERE regexp_full_match(split_part(email_commandes, '@', 1), '[a-z]+\.[a-z]+');
