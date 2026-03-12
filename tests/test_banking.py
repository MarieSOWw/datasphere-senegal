"""
tests/test_banking.py
═══════════════════════════════════════════════════════════════════════
Tests unitaires — Dashboard Bancaire BCEAO
Vérifie l'intégrité des données, les calculs de ratios et la logique métier.

Lancement :
    python -m pytest tests/test_banking.py -v
    python -m pytest tests/test_banking.py -v --tb=short
═══════════════════════════════════════════════════════════════════════
"""
import sys
import os
import math

import pandas as pd
import pytest

# ── Ajouter le dossier racine au path ─────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Données de test (échantillon représentatif) ─────────────────────
SAMPLE_DATA = [
    {
        "sigle": "SGBS", "annee": 2022,
        "bilan": 1186364, "fonds_propres": 118677,
        "emploi": 664236, "ressources": 950000,
        "produit_net_bancaire": 71746, "resultat_net": 18500,
        "charges_generales_exploitation": 43690,
        "cout_du_risque": -436, "impots_benefices": 6395,
        "interets_produits": 56026, "interets_charges": 13972,
        "commissions_produits": 26005, "commissions_charges": 3952,
        "autres_charges_exploitation": 941, "autres_produits_exploitation": 5446,
        "gains_pertes_actifs_immobilises": -145,
        "groupe_bancaire": "Groupes Internationaux",
    },
    {
        "sigle": "CBAO", "annee": 2022,
        "bilan": 1050000, "fonds_propres": 95000,
        "emploi": 600000, "ressources": 880000,
        "produit_net_bancaire": 65000, "resultat_net": 14000,
        "charges_generales_exploitation": 38000,
        "cout_du_risque": -2000, "impots_benefices": 4000,
        "interets_produits": 50000, "interets_charges": 12000,
        "commissions_produits": 20000, "commissions_charges": 3000,
        "autres_charges_exploitation": 1000, "autres_produits_exploitation": 4000,
        "gains_pertes_actifs_immobilises": 0,
        "groupe_bancaire": "Groupes Continentaux",
    },
    {
        "sigle": "BHS", "annee": 2022,
        "bilan": 420000, "fonds_propres": 45000,
        "emploi": 280000, "ressources": 380000,
        "produit_net_bancaire": 25000, "resultat_net": 5000,
        "charges_generales_exploitation": 15000,
        "cout_du_risque": -500, "impots_benefices": 1500,
        "interets_produits": 20000, "interets_charges": 5000,
        "commissions_produits": 8000, "commissions_charges": 1000,
        "autres_charges_exploitation": 500, "autres_produits_exploitation": 2000,
        "gains_pertes_actifs_immobilises": 0,
        "groupe_bancaire": "Groupes Locaux",
    },
    {
        "sigle": "SGBS", "annee": 2021,
        "bilan": 1050000, "fonds_propres": 105000,
        "emploi": 600000, "ressources": 850000,
        "produit_net_bancaire": 65000, "resultat_net": 15000,
        "charges_generales_exploitation": 40000,
        "cout_du_risque": -500, "impots_benefices": 5000,
        "interets_produits": 50000, "interets_charges": 12000,
        "commissions_produits": 22000, "commissions_charges": 3500,
        "autres_charges_exploitation": 800, "autres_produits_exploitation": 4500,
        "gains_pertes_actifs_immobilises": 0,
        "groupe_bancaire": "Groupes Internationaux",
    },
    {
        "sigle": "BNDE", "annee": 2022,
        "bilan": 180000, "fonds_propres": 20000,
        "emploi": 130000, "ressources": 160000,
        "produit_net_bancaire": 10000, "resultat_net": -1000,  # perte
        "charges_generales_exploitation": 7000,
        "cout_du_risque": -3000, "impots_benefices": 0,
        "interets_produits": 8000, "interets_charges": 3000,
        "commissions_produits": 3000, "commissions_charges": 500,
        "autres_charges_exploitation": 200, "autres_produits_exploitation": 800,
        "gains_pertes_actifs_immobilises": 0,
        "groupe_bancaire": "Groupes Locaux",
    },
]


@pytest.fixture
def df_sample():
    """Fixture : DataFrame de test."""
    df = pd.DataFrame(SAMPLE_DATA)
    # Conversion types numériques
    num_cols = [
        "bilan", "fonds_propres", "emploi", "ressources",
        "produit_net_bancaire", "resultat_net",
        "charges_generales_exploitation", "cout_du_risque",
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["annee"] = df["annee"].astype(int)
    return df


# ══════════════════════════════════════════════════════════════════════
# 1. TESTS D'INTÉGRITÉ DES DONNÉES
# ══════════════════════════════════════════════════════════════════════
class TestIntegriteDonnees:

    def test_colonnes_obligatoires_presentes(self, df_sample):
        """Vérifie que toutes les colonnes KPI obligatoires sont présentes."""
        cols_obligatoires = [
            "sigle", "annee", "bilan", "fonds_propres",
            "emploi", "ressources", "produit_net_bancaire", "resultat_net",
        ]
        for col in cols_obligatoires:
            assert col in df_sample.columns, f"Colonne obligatoire manquante : {col}"

    def test_pas_de_sigle_vide(self, df_sample):
        """Aucun sigle ne doit être vide ou NaN."""
        assert df_sample["sigle"].notna().all(), "Des sigles NaN détectés"
        assert (df_sample["sigle"].str.strip() != "").all(), "Des sigles vides détectés"

    def test_annees_valides(self, df_sample):
        """Les années doivent être comprises entre 2000 et 2030."""
        assert (df_sample["annee"] >= 2000).all(), "Année < 2000 détectée"
        assert (df_sample["annee"] <= 2030).all(), "Année > 2030 détectée"

    def test_bilan_positif(self, df_sample):
        """Le bilan doit toujours être positif."""
        assert (df_sample["bilan"] > 0).all(), "Bilan négatif ou nul détecté"

    def test_emploi_inferieur_au_bilan(self, df_sample):
        """L'emploi ne peut pas dépasser le bilan."""
        assert (df_sample["emploi"] <= df_sample["bilan"]).all(), \
            "Emploi supérieur au bilan — incohérence bilancielle"

    def test_fonds_propres_positifs(self, df_sample):
        """Les fonds propres doivent être positifs (banque solvable)."""
        assert (df_sample["fonds_propres"] > 0).all(), \
            "Fonds propres négatifs détectés — banque insolvable"

    def test_pas_de_doublons(self, df_sample):
        """Pas de doublon (sigle, annee)."""
        dupes = df_sample.duplicated(subset=["sigle", "annee"])
        assert not dupes.any(), \
            f"Doublons (sigle, annee) détectés : {df_sample[dupes][['sigle','annee']].to_dict()}"

    def test_groupe_bancaire_valide(self, df_sample):
        """Le groupe_bancaire doit appartenir à une liste de valeurs valides."""
        groupes_valides = {
            "Groupes Locaux", "Groupes Règionaux", "Groupes Régionaux",
            "Groupes Continentaux", "Groupes Internationaux",
        }
        for g in df_sample["groupe_bancaire"].dropna():
            assert g in groupes_valides, \
                f"Groupe bancaire invalide : '{g}'"


# ══════════════════════════════════════════════════════════════════════
# 2. TESTS DE CALCUL DES RATIOS
# ══════════════════════════════════════════════════════════════════════
class TestCalculRatios:

    def test_ratio_solvabilite(self, df_sample):
        """Ratio solvabilité = Fonds Propres / Bilan × 100."""
        row = df_sample[df_sample["sigle"] == "SGBS"].iloc[0]
        ratio = round(row["fonds_propres"] / row["bilan"] * 100, 4)
        expected = round(118677 / 1186364 * 100, 4)
        assert abs(ratio - expected) < 0.01, \
            f"Ratio solvabilité incorrect : {ratio} ≠ {expected}"

    def test_ratio_solvabilite_norme_bceao(self, df_sample):
        """Alerte si ratio solvabilité < 8% (norme BCEAO)."""
        for _, row in df_sample.iterrows():
            ratio = row["fonds_propres"] / row["bilan"] * 100
            if ratio < 8:
                # Ce n'est pas une erreur bloquante mais un avertissement
                print(f"⚠️ AVERTISSEMENT : {row['sigle']} {row['annee']} "
                      f"— Solvabilité {ratio:.2f}% < 8% (norme BCEAO)")

    def test_ratio_rendement_actifs(self, df_sample):
        """ROA = Résultat Net / Bilan × 100."""
        row = df_sample[df_sample["sigle"] == "SGBS"].iloc[0]
        roa = round(row["resultat_net"] / row["bilan"] * 100, 4)
        expected = round(18500 / 1186364 * 100, 4)
        assert abs(roa - expected) < 0.01, \
            f"ROA incorrect : {roa} ≠ {expected}"

    def test_ratio_liquidite(self, df_sample):
        """Ratio liquidité = Emploi / Ressources × 100."""
        row = df_sample[df_sample["sigle"] == "SGBS"].iloc[0]
        liq = round(row["emploi"] / row["ressources"] * 100, 4)
        expected = round(664236 / 950000 * 100, 4)
        assert abs(liq - expected) < 0.01, \
            f"Ratio liquidité incorrect : {liq} ≠ {expected}"

    def test_ratio_rentabilite_capitaux(self, df_sample):
        """ROE = Résultat Net / Fonds Propres × 100."""
        row = df_sample[df_sample["sigle"] == "SGBS"].iloc[0]
        roe = round(row["resultat_net"] / row["fonds_propres"] * 100, 4)
        expected = round(18500 / 118677 * 100, 4)
        assert abs(roe - expected) < 0.01, \
            f"ROE incorrect : {roe} ≠ {expected}"

    def test_coefficient_exploitation(self, df_sample):
        """Coeff. exploitation = Charges Générales / PNB × 100."""
        row = df_sample[df_sample["sigle"] == "SGBS"].iloc[0]
        coeff = round(row["charges_generales_exploitation"] / row["produit_net_bancaire"] * 100, 4)
        expected = round(43690 / 71746 * 100, 4)
        assert abs(coeff - expected) < 0.01, \
            f"Coeff. exploitation incorrect : {coeff} ≠ {expected}"

    def test_ratio_division_zero(self, df_sample):
        """Le calcul des ratios ne doit pas planter avec des ressources nulles."""
        df_test = df_sample.copy()
        df_test.loc[0, "ressources"] = 0
        # La division par zéro doit être gérée gracieusement
        ressources = df_test.loc[0, "ressources"]
        emploi = df_test.loc[0, "emploi"]
        ratio = emploi / ressources if ressources != 0 else float("nan")
        assert math.isnan(ratio), "Division par zéro non gérée"


# ══════════════════════════════════════════════════════════════════════
# 3. TESTS DE LOGIQUE MÉTIER
# ══════════════════════════════════════════════════════════════════════
class TestLogiqueMétier:

    def test_classement_correct(self, df_sample):
        """Le classement par bilan doit être décroissant."""
        annee = 2022
        d = df_sample[df_sample["annee"] == annee].sort_values("bilan", ascending=False)
        bilans = d["bilan"].tolist()
        assert bilans == sorted(bilans, reverse=True), \
            "Le classement par bilan n'est pas décroissant"

    def test_parts_marche_somme_100(self, df_sample):
        """Les parts de marché doivent sommer à 100%."""
        d = df_sample[df_sample["annee"] == 2022][["sigle", "bilan"]].dropna()
        total = d["bilan"].sum()
        parts = d["bilan"] / total * 100
        assert abs(parts.sum() - 100.0) < 0.01, \
            f"Les parts de marché ne somment pas à 100% : {parts.sum()}"

    def test_evolution_temporelle_sgbs(self, df_sample):
        """Test croissance SGBS : bilan 2022 > bilan 2021."""
        bilan_2021 = df_sample[(df_sample["sigle"] == "SGBS") & (df_sample["annee"] == 2021)]["bilan"].values[0]
        bilan_2022 = df_sample[(df_sample["sigle"] == "SGBS") & (df_sample["annee"] == 2022)]["bilan"].values[0]
        assert bilan_2022 > bilan_2021, \
            f"Régression du bilan SGBS : {bilan_2021} → {bilan_2022}"

    def test_delta_calcul_correct(self, df_sample):
        """Test calcul du delta (%) entre deux années."""
        bilan_2021 = 1050000
        bilan_2022 = 1186364
        delta = ((bilan_2022 - bilan_2021) / abs(bilan_2021)) * 100
        assert abs(delta - 12.987) < 0.01, \
            f"Calcul delta incorrect : {delta:.3f}% ≠ 12.987%"

    def test_banque_perte_detectee(self, df_sample):
        """La BNDE a un résultat net négatif — doit être détectée."""
        d = df_sample[(df_sample["sigle"] == "BNDE") & (df_sample["annee"] == 2022)]
        assert not d.empty, "BNDE 2022 non trouvée dans le dataset"
        rn = d["resultat_net"].values[0]
        assert rn < 0, f"BNDE devrait avoir un résultat net négatif, trouvé : {rn}"

    def test_radar_normalisation(self, df_sample):
        """Les scores radar normalisés doivent être entre 0 et 100."""
        annee = 2022
        all_year = df_sample[df_sample["annee"] == annee]
        banque = "SGBS"
        d = all_year[all_year["sigle"] == banque]

        dims = ["bilan", "produit_net_bancaire", "resultat_net",
                "fonds_propres", "emploi", "ressources"]

        for col in dims:
            v  = d[col].values[0]
            mx = all_year[col].max()
            score = round(float(v / mx * 100), 1) if mx and mx > 0 else 0
            assert 0 <= score <= 100, \
                f"Score radar hors bornes pour {col} : {score}"


# ══════════════════════════════════════════════════════════════════════
# 4. TESTS DE FORMATAGE
# ══════════════════════════════════════════════════════════════════════
class TestFormatage:

    def test_fmt_milliards(self):
        """fmt() doit retourner '1.19 B' pour 1 186 364 M FCFA."""
        # Simulation de la fonction fmt
        def fmt(val):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return "N/D"
            v = float(val)
            if abs(v) >= 1_000_000:
                return f"{v/1_000_000:.2f} B"
            if abs(v) >= 1_000:
                return f"{v/1_000:.1f} Mds"
            return f"{v:,.0f} M"

        assert fmt(1_186_364) == "1.19 B", f"Format inattendu : {fmt(1_186_364)}"
        assert fmt(65_000)    == "65.0 Mds", f"Format inattendu : {fmt(65_000)}"
        assert fmt(500)       == "500 M", f"Format inattendu : {fmt(500)}"
        assert fmt(None)      == "N/D", "fmt(None) doit retourner 'N/D'"

    def test_fmt_negatif(self):
        """fmt() doit gérer les valeurs négatives (coût du risque, pertes)."""
        def fmt(val):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return "N/D"
            v = float(val)
            if abs(v) >= 1_000_000:
                return f"{v/1_000_000:.2f} B"
            if abs(v) >= 1_000:
                return f"{v/1_000:.1f} Mds"
            return f"{v:,.0f} M"

        result = fmt(-1_000)
        assert result == "-1.0 Mds", f"Valeur négative mal formatée : {result}"

    def test_pct_format(self):
        """_pct() doit retourner '10.52 %' pour 10.5238."""
        def pct(val):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return "N/D"
            return f"{val:.2f} %"

        assert pct(10.5238) == "10.52 %"
        assert pct(None) == "N/D"
        assert pct(float("nan")) == "N/D"


# ══════════════════════════════════════════════════════════════════════
# 5. TESTS DE NETTOYAGE DES DONNÉES
# ══════════════════════════════════════════════════════════════════════
class TestNettoyageDonnees:

    GROUPE_NORM = {
        "Groupes Régionaux": "Groupes Règionaux",
        "Groupes regionaux": "Groupes Règionaux",
        "Groupes Regionaux": "Groupes Règionaux",
        "Locaux":            "Groupes Locaux",
        "Règionaux":         "Groupes Règionaux",
        "Régionaux":         "Groupes Règionaux",
        "Continentaux":      "Groupes Continentaux",
        "Internationaux":    "Groupes Internationaux",
    }

    def test_normalisation_groupe_regionaux(self):
        """La normalisation doit transformer 'Groupes Régionaux' → 'Groupes Règionaux'."""
        g = "Groupes Régionaux"
        result = self.GROUPE_NORM.get(g, g)
        assert result == "Groupes Règionaux", \
            f"Normalisation incorrecte : '{g}' → '{result}'"

    def test_normalisation_passage_inconnu(self):
        """Un groupe inconnu doit rester inchangé."""
        g = "Groupes Inconnus"
        result = self.GROUPE_NORM.get(g, g)
        assert result == "Groupes Inconnus", \
            f"Un groupe inconnu ne doit pas être modifié : '{result}'"

    def test_conversion_types_numeriques(self):
        """pd.to_numeric doit convertir correctement les valeurs string."""
        vals = pd.Series(["1186364", "65000.5", "N/A", None, ""])
        result = pd.to_numeric(vals, errors="coerce")
        assert result[0] == 1186364.0
        assert result[1] == 65000.5
        assert pd.isna(result[2])
        assert pd.isna(result[3])
        assert pd.isna(result[4])

    def test_sigle_strip(self):
        """Les sigles doivent être nettoyés des espaces."""
        sigles = pd.Series(["  SGBS  ", "CBAO", " BHS"])
        result = sigles.str.strip()
        assert result.tolist() == ["SGBS", "CBAO", "BHS"], \
            f"Strip des sigles incorrect : {result.tolist()}"


# ══════════════════════════════════════════════════════════════════════
# 6. TESTS DE COUVERTURE DES DONNÉES
# ══════════════════════════════════════════════════════════════════════
class TestCouvertureDonnees:

    def test_toutes_les_annees_dans_plage(self, df_sample):
        """Les années disponibles doivent être dans la plage 2015-2023."""
        annees = df_sample["annee"].unique()
        for a in annees:
            assert 2015 <= a <= 2023, f"Année hors plage : {a}"

    def test_au_moins_2_banques(self, df_sample):
        """Le dataset doit contenir au moins 2 banques pour permettre la comparaison."""
        nb_banques = df_sample["sigle"].nunique()
        assert nb_banques >= 2, \
            f"Pas assez de banques pour la comparaison : {nb_banques}"

    def test_au_moins_une_annee(self, df_sample):
        """Au moins une année de données disponibles."""
        nb_annees = df_sample["annee"].nunique()
        assert nb_annees >= 1, "Aucune année de données disponible"

    def test_somme_bilan_coherente(self, df_sample):
        """Le total bilan sectoriel doit être supérieur à 1 milliard (1 000 000 M FCFA)."""
        total = df_sample[df_sample["annee"] == 2022]["bilan"].sum()
        assert total > 1_000_000, \
            f"Total bilan sectoriel trop faible : {total:,.0f} M FCFA"


# ══════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False
    )
    sys.exit(result.returncode)
