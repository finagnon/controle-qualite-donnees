# Dictionnaire de données

Référentiel fictif d'une pharmacie hospitalière. Colonne *Donnée personnelle* : aucune donnée personnelle n'est collectée (minimisation RGPD).

## Table `articles`

| Colonne | Type | Obligatoire | Description | Règle qualité | Exemple | Propriétaire | Donnée personnelle |
|---|---|---|---|---|---|---|---|
| `code_article` | texte | Oui | Identifiant unique de l'article dans le référentiel | R04 unicité | `ART-00042` | Pharmacien référent achats | Non |
| `libelle` | texte | Oui | Désignation de l'article (DCI + dosage) | R01 complétude ; R05 doublons | `Paracétamol 1 g` | Pharmacien référent achats | Non |
| `categorie` | texte | Oui | Famille de produits | Liste de valeurs | `Antibiotiques` | Pharmacien référent achats | Non |
| `code_ucd` | texte | Oui | Code UCD (unité commune de dispensation) - fictif dans ce projet | R06 format 13 chiffres | `3400812345678` | Pharmacien référent achats | Non |
| `code_atc` | texte | Oui | Classification ATC de l'OMS | R07 format A00AA00 | `N02BE01` | Pharmacien référent achats | Non |
| `unite` | texte | Oui | Unité de dispensation | R02 complétude ; R09 liste de référence | `flacon` | Pharmacien référent achats | Non |
| `prix_unitaire_eur` | décimal | Oui | Prix unitaire HT en euros | R03 complétude ; R08 > 0 | `12.50` | Acheteur hospitalier | Non |
| `fournisseur_id` | texte | Oui | Fournisseur titulaire du marché | R11 cohérence ; R12 intégrité référentielle | `FRN-007` | Acheteur hospitalier | Non |
| `statut` | texte | Oui | actif / inactif | Liste de valeurs | `actif` | Pharmacien référent achats | Non |
| `date_creation` | date | Oui | Date de création de la fiche | R10 cohérence | `2022-03-15` | Data steward | Non |
| `date_maj` | date | Oui | Date de dernière revue de la fiche | R10 cohérence ; R13 fraîcheur < 24 mois | `2025-06-01` | Data steward | Non |

## Table `fournisseurs`

| Colonne | Type | Obligatoire | Description | Règle qualité | Exemple | Propriétaire | Donnée personnelle |
|---|---|---|---|---|---|---|---|
| `fournisseur_id` | texte | Oui | Identifiant unique du fournisseur | Clé primaire | `FRN-007` | Acheteur hospitalier | Non |
| `raison_sociale` | texte | Oui | Raison sociale du fournisseur (fictive) | R17 unicité | `Fournisseur G (fictif)` | Acheteur hospitalier | Non |
| `email_commandes` | texte | Oui | Adresse e-mail de service pour les commandes | R14 format ; R15 RGPD pas d'e-mail nominatif | `commandes@fournisseur-007.example.com` | Acheteur hospitalier | Non (adresse de service uniquement) |
| `ville` | texte | Non | Ville du siège | - | `Lyon` | Acheteur hospitalier | Non |
| `pays` | texte | Oui | Pays du siège | R16 complétude | `France` | Acheteur hospitalier | Non |
| `statut` | texte | Oui | actif / inactif | Liste de valeurs | `actif` | Acheteur hospitalier | Non |

## Table `commandes`

| Colonne | Type | Obligatoire | Description | Règle qualité | Exemple | Propriétaire | Donnée personnelle |
|---|---|---|---|---|---|---|---|
| `num_commande` | texte | Oui | Identifiant unique de la commande | Clé primaire | `CDE-000123` | Gestionnaire approvisionnement | Non |
| `code_article` | texte | Oui | Article commandé | R18 intégrité référentielle | `ART-00042` | Gestionnaire approvisionnement | Non |
| `fournisseur_id` | texte | Oui | Fournisseur de la commande | Intégrité référentielle | `FRN-007` | Gestionnaire approvisionnement | Non |
| `date_commande` | date | Oui | Date d'émission de la commande | R20 cohérence | `2025-04-02` | Gestionnaire approvisionnement | Non |
| `date_livraison` | date | Non | Date de livraison effective | R20 cohérence | `2025-04-09` | Gestionnaire approvisionnement | Non |
| `quantite` | entier | Oui | Quantité commandée | R19 > 0 | `120` | Gestionnaire approvisionnement | Non |
| `prix_unitaire_eur` | décimal | Oui | Prix unitaire facturé | R21 écart ≤ 20 % vs référentiel | `12.80` | Acheteur hospitalier | Non |
