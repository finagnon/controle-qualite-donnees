"""
Génère un référentiel 100 % FICTIF (articles, fournisseurs, commandes) d'une pharmacie
hospitalière, puis y injecte volontairement des anomalies de qualité de données
(champs vides, doublons, formats invalides, incohérences, orphelins...).

Aucune donnée réelle : les codes, fournisseurs, adresses e-mail (domaine réservé
example.com) et noms de personnes sont inventés.

Usage : python generate_data.py   (graine fixe -> résultats reproductibles)
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
DATA = Path(__file__).parent / "data"
UNITES = ["flacon", "ampoule", "poche", "unité", "boîte", "comprimé"]
CATEGORIES = ["Anticancéreux", "Antibiotiques", "Antalgiques", "Solutés", "Dispositifs médicaux", "Nutrition"]
DCI = ["Paracétamol", "Amoxicilline", "Ceftriaxone", "Cisplatine", "Carboplatine", "Vancomycine", "Morphine",
       "Néfopam", "Kétoprofène", "Glucose", "Chlorure de sodium", "Héparine", "Enoxaparine", "Furosémide",
       "Oméprazole", "Métronidazole", "Gentamicine", "Ondansétron", "Dexaméthasone", "Insuline"]
DOSAGES = ["10 mg", "20 mg", "50 mg", "100 mg", "500 mg", "1 g", "2 g", "250 mL", "500 mL", "1 L"]
ATC_PREFIX = ["N02BE", "J01CA", "J01DD", "L01XA", "J01XA", "N02AA", "M01AE", "B05BA", "B01AB", "C03CA"]
VILLES = ["Lyon", "Paris", "Lille", "Nantes", "Bordeaux", "Toulouse", "Strasbourg", "Rennes"]
PRENOMS_NOMS = [("jean", "martin"), ("claire", "durand"), ("paul", "bernard"), ("lea", "petit")]  # fictifs


def luhn_free_ucd() -> str:
    """Code UCD fictif à 13 chiffres (format seulement, aucune correspondance réelle)."""
    return "34008" + "".join(str(d) for d in rng.integers(0, 10, 8))


def build():
    # ---------------- fournisseurs ----------------
    frn = []
    for i in range(1, 26):
        nom = f"Fournisseur {chr(64 + (i - 1) % 26 + 1)}{'' if i <= 26 else i} (fictif)"
        frn.append({
            "fournisseur_id": f"FRN-{i:03d}", "raison_sociale": nom,
            "email_commandes": f"commandes@fournisseur-{i:03d}.example.com",
            "ville": rng.choice(VILLES), "pays": "France",
            "statut": "inactif" if i in (7, 19) else "actif",
        })
    frn = pd.DataFrame(frn)

    # ---------------- articles ----------------
    arts = []
    for i in range(1, 301):
        cat = rng.choice(CATEGORIES)
        creation = pd.Timestamp("2019-01-01") + pd.Timedelta(days=int(rng.integers(0, 1800)))
        debut_revue = max(creation, pd.Timestamp("2024-03-01"))
        maj = debut_revue + pd.Timedelta(days=int(rng.integers(0, (pd.Timestamp("2025-12-31") - debut_revue).days)))
        arts.append({
            "code_article": f"ART-{i:05d}",
            "libelle": f"{rng.choice(DCI)} {rng.choice(DOSAGES)}",
            "categorie": cat,
            "code_ucd": luhn_free_ucd(),
            "code_atc": f"{rng.choice(ATC_PREFIX)}{rng.integers(1, 99):02d}",
            "unite": rng.choice(UNITES),
            "prix_unitaire_eur": round(float(np.exp(rng.uniform(np.log(0.5), np.log(900)))), 2),
            "fournisseur_id": rng.choice(frn["fournisseur_id"]),
            "statut": "actif" if rng.random() > 0.08 else "inactif",
            "date_creation": creation.date().isoformat(),
            "date_maj": maj.date().isoformat(),
        })
    arts = pd.DataFrame(arts)
    # libellés uniques pour que les quasi-doublons injectés soient les seuls
    arts["libelle"] = arts["libelle"] + " (" + arts["code_article"].str[-3:] + ")"

    # ---------------- commandes ----------------
    cmd = []
    for i in range(1, 1501):
        a = arts.iloc[int(rng.integers(0, len(arts)))]
        dc = pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 360)))
        cmd.append({
            "num_commande": f"CDE-{i:06d}", "code_article": a.code_article, "fournisseur_id": a.fournisseur_id,
            "date_commande": dc.date().isoformat(),
            "date_livraison": (dc + pd.Timedelta(days=int(rng.integers(1, 15)))).date().isoformat(),
            "quantite": int(rng.integers(1, 400)),
            "prix_unitaire_eur": round(a.prix_unitaire_eur * rng.uniform(0.95, 1.05), 2),
        })
    cmd = pd.DataFrame(cmd)
    return frn, arts, cmd


def inject(frn, arts, cmd):
    """Injecte des anomalies réalistes (les nombres sont volontairement variés)."""
    pick = lambda df, n: rng.choice(df.index, n, replace=False)

    arts.loc[pick(arts, 5), "libelle"] = None                                   # complétude
    arts.loc[pick(arts, 8), "unite"] = None
    arts.loc[pick(arts, 6), "prix_unitaire_eur"] = None
    arts.loc[pick(arts, 3), "prix_unitaire_eur"] = 0.0                           # validité
    arts.loc[pick(arts, 10), "code_ucd"] = [str(rng.integers(10**8, 10**11)) for _ in range(10)]
    arts.loc[pick(arts, 12), "code_atc"] = ["N2BE01", "j01ca04", "L01X", "B05-BA03", "XX0000", "N02BE1",
                                            "J1CA04", "M01AE0", "c03ca01", "N02 BE01", "A", "J01DD040"]
    arts.loc[pick(arts, 15), "unite"] = rng.choice(["Flacon", "FL", "fl.", "Amp", "POCHE", "u"], 15)  # non standard
    idx = pick(arts, 5)                                                           # cohérence de dates
    arts.loc[idx, "date_maj"] = (pd.to_datetime(arts.loc[idx, "date_creation"]) - pd.Timedelta(days=30)).dt.date.astype(str)
    arts.loc[pick(arts, 4), "fournisseur_id"] = ["FRN-099", "FRN-120", "FRN-0X1", "FRN-777"]  # orphelins
    old = pick(arts, 20)                                                          # fraîcheur
    arts.loc[old, "date_creation"] = "2019-02-01"
    arts.loc[old, "date_maj"] = "2021-06-30"
    # doublons exacts de clé (même code article saisi deux fois)
    dups = arts.loc[pick(arts, 4)].copy()
    # quasi-doublons : même libellé à la casse/espaces près, codes différents
    near = arts.loc[pick(arts, 6)].copy()
    near["code_article"] = [f"ART-{900 + k:05d}" for k in range(len(near))]
    near["libelle"] = near["libelle"].str.upper().str.replace(" ", "  ", n=1)
    arts = pd.concat([arts, dups, near], ignore_index=True)

    frn.loc[pick(frn, 3), "email_commandes"] = ["commandes@fournisseur", "contact.example.com", "ventes@@example.com"]
    nomin = pick(frn, 4)                                                          # RGPD : e-mails nominatifs
    frn.loc[nomin, "email_commandes"] = [f"{p}.{n}@fournisseur-x.example.com" for p, n in PRENOMS_NOMS]
    frn.loc[pick(frn, 2), "pays"] = None
    frn = pd.concat([frn, frn.loc[pick(frn, 2)].assign(
        fournisseur_id=lambda d: [f"FRN-{200 + k:03d}" for k in range(len(d))])], ignore_index=True)

    cmd.loc[pick(cmd, 10), "code_article"] = [f"ART-{80000 + k:05d}" for k in range(10)]   # orphelins
    cmd.loc[pick(cmd, 6), "quantite"] = [0, -5, 0, -1, 0, -12]
    px = pick(cmd, 25)
    cmd.loc[px, "prix_unitaire_eur"] = (cmd.loc[px, "prix_unitaire_eur"] * rng.choice([0.5, 1.4, 1.8, 2.5], 25)).round(2)
    idx = pick(cmd, 5)
    cmd.loc[idx, "date_livraison"] = (pd.to_datetime(cmd.loc[idx, "date_commande"]) - pd.Timedelta(days=3)).dt.date.astype(str)
    return frn, arts, cmd


def main():
    DATA.mkdir(exist_ok=True)
    frn, arts, cmd = inject(*build())
    frn.to_csv(DATA / "fournisseurs.csv", index=False)
    arts.to_csv(DATA / "articles.csv", index=False)
    cmd.to_csv(DATA / "commandes.csv", index=False)
    print(f"{len(arts)} articles, {len(frn)} fournisseurs, {len(cmd)} commandes (avec anomalies injectées)")


if __name__ == "__main__":
    main()
