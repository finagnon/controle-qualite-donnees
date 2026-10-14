"""
Exécute les règles de qualité (sql/regles_qualite.sql) sur les données brutes,
applique le plan de remédiation automatique (sql/remediation.sql), puis relance
les contrôles pour mesurer le gain. Produit :
  - rapport/rapport_qualite.csv   (une ligne par règle : avant / après)
  - rapport/anomalies_avant.csv et rapport/anomalies_apres.csv (détail ligne à ligne)
  - data_corrigees/*.csv           (tables après remédiation)
  - docs/dictionnaire_donnees.md   (généré depuis docs/dictionnaire_donnees.csv)
  - dashboard/index.html           (scorecard autonome)

Usage : python run_controles.py
"""
import json
import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).parent
TABLES = ["articles", "fournisseurs", "commandes"]
POIDS = {"Critique": 3, "Majeure": 2, "Mineure": 1}
PROPRIETAIRES = {"articles": "Pharmacien référent achats", "fournisseurs": "Acheteur hospitalier",
                 "commandes": "Gestionnaire approvisionnement"}


def load(con):
    for t in TABLES:
        con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_csv('{(ROOT / 'data' / (t + '.csv')).as_posix()}', "
                    "header = true, all_varchar = true)")


def parse_rules():
    text = (ROOT / "sql" / "regles_qualite.sql").read_text(encoding="utf-8")
    parts = re.split(r"^-- rule:\s*(.+)$", text, flags=re.M)[1:]
    rules = []
    for header, body in zip(parts[::2], parts[1::2]):
        code, dim, table, crit, label = [p.strip() for p in header.split("|")]
        rules.append({"code": code, "dimension": dim, "table": table, "criticite": crit,
                      "libelle": label, "sql": body.strip().rstrip(";")})
    return rules


def run(con, rules, phase):
    rows, details = [], []
    for r in rules:
        res = con.execute(r["sql"]).df()
        n = con.execute(f"SELECT COUNT(*) FROM {r['table']}").fetchone()[0]
        nb = len(res)
        rows.append({"code": r["code"], f"lignes_controlees_{phase}": n, f"anomalies_{phase}": nb,
                     f"taux_conformite_{phase}": round(1 - nb / n, 4) if n else 1.0})
        details += [{"code": r["code"], "table": r["table"], "cle": k, "detail": d}
                    for k, d in zip(res["cle"], res["detail"])]
    return pd.DataFrame(rows), pd.DataFrame(details)


def score(df, phase, by=None):
    w = df["criticite"].map(POIDS)
    s = (df[f"taux_conformite_{phase}"] * w)
    if by is None:
        return round(float(s.sum() / w.sum()), 4)
    return (s.groupby(df[by]).sum() / w.groupby(df[by]).sum()).round(4).to_dict()


def dictionnaire_md():
    d = pd.read_csv(ROOT / "docs" / "dictionnaire_donnees.csv")
    lines = ["# Dictionnaire de données", "",
             "Référentiel fictif d'une pharmacie hospitalière. Colonne *Donnée personnelle* : "
             "aucune donnée personnelle n'est collectée (minimisation RGPD).", ""]
    for t, g in d.groupby("table", sort=False):
        lines += [f"## Table `{t}`", "", "| Colonne | Type | Obligatoire | Description | Règle qualité | Exemple | Propriétaire | Donnée personnelle |",
                  "|---|---|---|---|---|---|---|---|"]
        lines += [f"| `{r.colonne}` | {r.type} | {r.obligatoire} | {r.description} | {r.regle_qualite} | `{r.exemple}` | "
                  f"{r.proprietaire_metier} | {r.donnee_personnelle} |" for r in g.itertuples()]
        lines.append("")
    (ROOT / "docs" / "dictionnaire_donnees.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    con = duckdb.connect()
    load(con)
    rules = parse_rules()
    avant, det_avant = run(con, rules, "avant")

    for stmt in [s.strip() for s in re.split(r";\s*\n", (ROOT / "sql" / "remediation.sql").read_text(encoding="utf-8"))]:
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body:
            con.execute(body)
    apres, det_apres = run(con, rules, "apres")

    meta = pd.DataFrame(rules).drop(columns="sql")
    rapport = meta.merge(avant, on="code").merge(apres, on="code")
    rapport["proprietaire"] = rapport["table"].map(PROPRIETAIRES)
    rapport["statut_apres"] = rapport["anomalies_apres"].map(lambda n: "Conforme" if n == 0 else "À traiter par le métier")

    (ROOT / "rapport").mkdir(exist_ok=True)
    rapport.to_csv(ROOT / "rapport" / "rapport_qualite.csv", index=False)
    det_avant.to_csv(ROOT / "rapport" / "anomalies_avant.csv", index=False)
    det_apres.to_csv(ROOT / "rapport" / "anomalies_apres.csv", index=False)
    (ROOT / "data_corrigees").mkdir(exist_ok=True)
    for t in TABLES:
        con.execute(f"SELECT * FROM {t}").df().to_csv(ROOT / "data_corrigees" / f"{t}.csv", index=False)
    dictionnaire_md()

    dims = list(dict.fromkeys(rapport["dimension"]))
    sa, sp = score(rapport, "avant", "dimension"), score(rapport, "apres", "dimension")
    exemples = det_avant.groupby("code").head(3).groupby("code").apply(
        lambda g: [f"{k} — {d}" for k, d in zip(g["cle"], g["detail"])], include_groups=False).to_dict()
    payload = {
        "score_avant": score(rapport, "avant"), "score_apres": score(rapport, "apres"),
        "anomalies_avant": int(rapport["anomalies_avant"].sum()), "anomalies_apres": int(rapport["anomalies_apres"].sum()),
        "nb_regles": len(rapport), "lignes": {t: int(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in TABLES},
        "dimensions": [{"dimension": d, "avant": sa[d], "apres": sp[d],
                        "nb_regles": int((rapport["dimension"] == d).sum())} for d in dims],
        "dictionnaire": json.loads(pd.read_csv(ROOT / "docs" / "dictionnaire_donnees.csv").to_json(orient="records", force_ascii=False)),
        "anomalies_par_dimension": [{"dimension": d, "avant": int(rapport.loc[rapport["dimension"] == d, "anomalies_avant"].sum()),
                                     "apres": int(rapport.loc[rapport["dimension"] == d, "anomalies_apres"].sum())} for d in dims],
        "regles_conformes_avant": int((rapport["anomalies_avant"] == 0).sum()),
        "regles_conformes_apres": int((rapport["anomalies_apres"] == 0).sum()),
        "regles": [dict(r, exemples=exemples.get(r["code"], [])) for r in json.loads(rapport.to_json(orient="records", force_ascii=False))],
    }
    html = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False))
    (ROOT / "dashboard" / "index.html").write_text(html, encoding="utf-8")

    print(f"Score qualité pondéré : {payload['score_avant']:.1%} avant -> {payload['score_apres']:.1%} après remédiation")
    print(f"Anomalies : {payload['anomalies_avant']} avant -> {payload['anomalies_apres']} après")
    print(rapport[["code", "dimension", "criticite", "anomalies_avant", "anomalies_apres", "statut_apres"]].to_string(index=False))


if __name__ == "__main__":
    main()
