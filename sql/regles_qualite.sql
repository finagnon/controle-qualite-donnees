-- =====================================================================
-- Règles de contrôle qualité des données (SQL DuckDB)
-- Les tables sont chargées "brutes" (toutes les colonnes en texte), comme dans
-- une zone de staging : chaque règle renvoie les lignes NON conformes.
--
-- En-tête de chaque règle (lu par run_controles.py) :
--   "rule: <code> | <dimension> | <table contrôlée> | <criticité> | <libellé>"
-- Criticité : Critique (poids 3), Majeure (poids 2), Mineure (poids 1)
-- =====================================================================

-- rule: R01 | Complétude | articles | Critique | Libellé de l'article renseigné
SELECT code_article AS cle, 'Libellé vide' AS detail
FROM articles WHERE libelle IS NULL OR trim(libelle) = '';

-- rule: R02 | Complétude | articles | Majeure | Unité de dispensation renseignée
SELECT code_article AS cle, 'Unité vide' AS detail
FROM articles WHERE unite IS NULL OR trim(unite) = '';

-- rule: R03 | Complétude | articles | Critique | Prix unitaire renseigné
SELECT code_article AS cle, 'Prix vide' AS detail
FROM articles WHERE prix_unitaire_eur IS NULL OR trim(prix_unitaire_eur) = '';

-- rule: R04 | Unicité | articles | Critique | Code article unique
SELECT code_article AS cle, 'Code présent ' || COUNT(*) || ' fois' AS detail
FROM articles GROUP BY code_article HAVING COUNT(*) > 1;

-- rule: R05 | Unicité | articles | Majeure | Pas de doublon de libellé (casse et espaces ignorés)
SELECT string_agg(code_article, ' / ' ORDER BY code_article) AS cle,
       'Doublon probable : ' || lower(regexp_replace(trim(libelle), '\s+', ' ', 'g')) AS detail
FROM (SELECT DISTINCT code_article, libelle FROM articles WHERE libelle IS NOT NULL)
GROUP BY lower(regexp_replace(trim(libelle), '\s+', ' ', 'g'))
HAVING COUNT(DISTINCT code_article) > 1;

-- rule: R06 | Validité | articles | Majeure | Code UCD au format 13 chiffres
SELECT code_article AS cle, 'UCD invalide : ' || coalesce(code_ucd, 'vide') AS detail
FROM articles WHERE code_ucd IS NULL OR NOT regexp_full_match(code_ucd, '[0-9]{13}');

-- rule: R07 | Validité | articles | Majeure | Code ATC au format OMS (ex. N02BE01)
SELECT code_article AS cle, 'ATC invalide : ' || coalesce(code_atc, 'vide') AS detail
FROM articles WHERE code_atc IS NULL OR NOT regexp_full_match(code_atc, '[A-Z][0-9]{2}[A-Z]{2}[0-9]{2}');

-- rule: R08 | Validité | articles | Critique | Prix unitaire strictement positif
SELECT code_article AS cle, 'Prix non positif : ' || prix_unitaire_eur AS detail
FROM articles WHERE TRY_CAST(prix_unitaire_eur AS DOUBLE) <= 0;

-- rule: R09 | Validité | articles | Mineure | Unité conforme à la liste de référence
SELECT code_article AS cle, 'Unité hors référentiel : ' || unite AS detail
FROM articles
WHERE unite IS NOT NULL AND unite NOT IN ('flacon', 'ampoule', 'poche', 'unité', 'boîte', 'comprimé');

-- rule: R10 | Cohérence | articles | Majeure | Date de mise à jour postérieure à la date de création
SELECT code_article AS cle, 'Mise à jour ' || date_maj || ' avant création ' || date_creation AS detail
FROM articles WHERE TRY_CAST(date_maj AS DATE) < TRY_CAST(date_creation AS DATE);

-- rule: R11 | Cohérence | articles | Majeure | Article actif rattaché à un fournisseur actif
SELECT a.code_article AS cle, 'Article actif, fournisseur ' || f.fournisseur_id || ' inactif' AS detail
FROM articles a JOIN fournisseurs f USING (fournisseur_id)
WHERE a.statut = 'actif' AND f.statut = 'inactif';

-- rule: R12 | Intégrité référentielle | articles | Critique | Fournisseur de l'article présent dans le référentiel
SELECT a.code_article AS cle, 'Fournisseur inconnu : ' || a.fournisseur_id AS detail
FROM articles a LEFT JOIN fournisseurs f USING (fournisseur_id)
WHERE f.fournisseur_id IS NULL;

-- rule: R13 | Fraîcheur | articles | Mineure | Fiche article revue depuis moins de 24 mois
SELECT code_article AS cle, 'Dernière mise à jour : ' || date_maj AS detail
FROM articles
WHERE statut = 'actif' AND TRY_CAST(date_maj AS DATE) < DATE '2025-12-31' - INTERVAL 24 MONTH;

-- rule: R14 | Validité | fournisseurs | Majeure | Adresse e-mail de commande valide
SELECT fournisseur_id AS cle, 'E-mail invalide : ' || coalesce(email_commandes, 'vide') AS detail
FROM fournisseurs
WHERE email_commandes IS NULL
   OR NOT regexp_full_match(email_commandes, '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}');

-- rule: R15 | Conformité RGPD | fournisseurs | Critique | Pas d'adresse e-mail nominative (minimisation des données)
SELECT fournisseur_id AS cle, 'E-mail nominatif (prenom.nom@) : à remplacer par une adresse de service' AS detail
FROM fournisseurs
WHERE regexp_full_match(split_part(email_commandes, '@', 1), '[a-z]+\.[a-z]+');

-- rule: R16 | Complétude | fournisseurs | Mineure | Pays du fournisseur renseigné
SELECT fournisseur_id AS cle, 'Pays vide' AS detail
FROM fournisseurs WHERE pays IS NULL OR trim(pays) = '';

-- rule: R17 | Unicité | fournisseurs | Majeure | Raison sociale unique
SELECT string_agg(fournisseur_id, ' / ' ORDER BY fournisseur_id) AS cle,
       'Même raison sociale : ' || raison_sociale AS detail
FROM fournisseurs GROUP BY raison_sociale HAVING COUNT(*) > 1;

-- rule: R18 | Intégrité référentielle | commandes | Critique | Article commandé présent dans le référentiel
SELECT c.num_commande AS cle, 'Article inconnu : ' || c.code_article AS detail
FROM commandes c
WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.code_article = c.code_article);

-- rule: R19 | Validité | commandes | Majeure | Quantité commandée strictement positive
SELECT num_commande AS cle, 'Quantité : ' || quantite AS detail
FROM commandes WHERE TRY_CAST(quantite AS INTEGER) <= 0;

-- rule: R20 | Cohérence | commandes | Majeure | Livraison postérieure à la commande
SELECT num_commande AS cle, 'Livrée le ' || date_livraison || ', commandée le ' || date_commande AS detail
FROM commandes WHERE TRY_CAST(date_livraison AS DATE) < TRY_CAST(date_commande AS DATE);

-- rule: R21 | Cohérence | commandes | Mineure | Prix de commande cohérent avec le référentiel (écart ≤ 20 %)
SELECT c.num_commande AS cle,
       'Écart de prix ' || round(100 * (TRY_CAST(c.prix_unitaire_eur AS DOUBLE) / TRY_CAST(a.prix_unitaire_eur AS DOUBLE) - 1)) || ' %' AS detail
FROM commandes c
JOIN (SELECT DISTINCT ON (code_article) code_article, prix_unitaire_eur FROM articles) a USING (code_article)
WHERE TRY_CAST(a.prix_unitaire_eur AS DOUBLE) > 0
  AND abs(TRY_CAST(c.prix_unitaire_eur AS DOUBLE) / TRY_CAST(a.prix_unitaire_eur AS DOUBLE) - 1) > 0.20;
