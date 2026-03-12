"""
dashboard/banking/rapport.py
Génération du rapport PDF par banque — données MongoDB 2015-2022

"""
import base64
import io
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from utils.db import get_collection

# ── Couleurs charte bancaire ───────────────────────────────────────────────────
C_BLEU   = colors.HexColor("#1A6FBA")
C_FONCE  = colors.HexColor("#0F2044")
C_VERT   = colors.HexColor("#10B981")
C_ORANGE = colors.HexColor("#F59E0B")
C_VIOLET = colors.HexColor("#8B5CF6")
C_GRIS   = colors.HexColor("#64748B")
C_FOND   = colors.HexColor("#F4F6FA")
C_BLANC  = colors.white
C_ALERTE = colors.HexColor("#FEF3C7")
C_ALERTE_BORD = colors.HexColor("#D97706")


def _fmt(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/D"
    return f"{val:,.0f} M FCFA"


def _pct(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/D"
    return f"{val:.2f} %"


def generer_rapport_pdf(banque: str, annee: int) -> str:
    """
    Génère un rapport PDF complet pour une banque sélectionnée.

    Si aucune donnée n'existe pour l'année demandée, le rapport
    est quand même généré avec :
      - Un avertissement visible en en-tête
      - L'évolution historique sur toutes les années disponibles
      - Le positionnement interbancaire sur l'année la plus proche disponible

    Retourne le contenu PDF en base64 (pour dcc.Download).
    """
    col, client = get_collection()
    docs = list(col.find({"sigle": banque}, {"_id": 0}))
    client.close()

    if not docs:
        raise ValueError(f"Aucune donnée dans MongoDB pour la banque : {banque}")

    df             = pd.DataFrame(docs)
    row_df         = df[df["annee"] == annee]
    annee_manquante = row_df.empty

    # ── Si l'année est absente → utilise la dernière année disponible ──────────
    if annee_manquante:
        annees_dispo = sorted(df["annee"].dropna().unique().astype(int).tolist())
        annee_ref    = annees_dispo[-1]
        row_df       = df[df["annee"] == annee_ref]
        row          = row_df.iloc[0]
    else:
        annee_ref = annee
        row       = row_df.iloc[0]

    # ── Recalcul des ratios si absents ─────────────────────────────────────────
    for c in ["bilan", "fonds_propres", "resultat_net",
              "produit_net_bancaire", "charges_generales_exploitation",
              "emploi", "ressources"]:
        if c in row.index:
            try:
                row[c] = float(row[c])
            except Exception:
                pass

    if pd.isna(row.get("ratio_solvabilite")) and row.get("fonds_propres") and row.get("bilan"):
        row["ratio_solvabilite"] = round(float(row["fonds_propres"]) / float(row["bilan"]) * 100, 4)
    if pd.isna(row.get("ratio_rendement_actifs")) and row.get("resultat_net") and row.get("bilan"):
        row["ratio_rendement_actifs"] = round(float(row["resultat_net"]) / float(row["bilan"]) * 100, 4)
    if pd.isna(row.get("ratio_rentabilite_capitaux")) and row.get("resultat_net") and row.get("fonds_propres"):
        row["ratio_rentabilite_capitaux"] = round(float(row["resultat_net"]) / float(row["fonds_propres"]) * 100, 4)
    if pd.isna(row.get("coefficient_exploitation")) and row.get("charges_generales_exploitation") and row.get("produit_net_bancaire"):
        row["coefficient_exploitation"] = round(float(row["charges_generales_exploitation"]) / float(row["produit_net_bancaire"]) * 100, 4)
    if pd.isna(row.get("ratio_emplois_ressources")) and row.get("emploi") and row.get("ressources"):
        row["ratio_emplois_ressources"] = round(float(row["emploi"]) / float(row["ressources"]) * 100, 4)

    # ── Création document ──────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.8*cm, bottomMargin=2*cm,
        title=f"Rapport Bancaire {banque} {annee}",
    )
    story = []

    # ── Style helpers ──────────────────────────────────────────────────────────
    def style_titre(txt, size=18, color=C_BLANC):
        return Paragraph(txt, ParagraphStyle(
            "t", fontSize=size, fontName="Helvetica-Bold",
            textColor=color, spaceAfter=2
        ))

    def style_section(txt):
        return Paragraph(txt, ParagraphStyle(
            "s", fontSize=11, fontName="Helvetica-Bold",
            textColor=C_FONCE, spaceBefore=10, spaceAfter=6,
        ))

    def style_body(txt):
        return Paragraph(txt, ParagraphStyle(
            "b", fontSize=8.5, fontName="Helvetica",
            textColor="#374151", leading=13
        ))

    def style_small(txt, color=C_GRIS):
        return Paragraph(txt, ParagraphStyle(
            "sm", fontSize=7.5, fontName="Helvetica",
            textColor=color
        ))

    def style_alerte(txt):
        return Paragraph(txt, ParagraphStyle(
            "al", fontSize=8.5, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#92400E"), leading=14,
            backColor=C_ALERTE,
            borderPadding=(6, 8, 6, 8),
        ))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 : EN-TÊTE
    # ══════════════════════════════════════════════════════════════════════════
    entete_data = [[
        style_titre("RAPPORT BANCAIRE", 22),
        style_titre(banque, 30, C_VERT),
    ]]
    entete = Table(entete_data, colWidths=["55%", "45%"])
    entete.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_FONCE),
        ("TOPPADDING",    (0,0),(-1,-1), 20),
        ("BOTTOMPADDING", (0,0),(-1,-1), 18),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
        ("ROUNDEDCORNERS",[8]),
    ]))
    story.append(entete)
    story.append(Spacer(1, 0.35*cm))

    annees_dispo_str = ", ".join(
        str(a) for a in sorted(df["annee"].dropna().unique().astype(int))
    )
    meta_txt = (
        f"Groupe : <b>{row.get('groupe_bancaire','N/D')}</b>  ·  "
        f"Année demandée : <b>{annee}</b>  ·  "
        f"Source : BCEAO & Base Sénégal  ·  "
        f"Années disponibles : {annees_dispo_str}"
    )
    story.append(style_small(meta_txt, color=C_GRIS))
    story.append(Spacer(1, 0.2*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLEU))
    story.append(Spacer(1, 0.3*cm))

    # ── Avertissement si données manquantes ────────────────────────────────────
    if annee_manquante:
        alerte_data = [[
            style_alerte(
                f"⚠️  Données non disponibles pour {banque} en {annee}. "
                f"La banque {banque} n'apparaît pas dans les rapports BCEAO "
                f"pour cette période (couverture PDF : 2021-2022). "
                f"Ce rapport présente les indicateurs de la dernière année "
                f"disponible ({annee_ref}) ainsi que l'évolution historique complète."
            )
        ]]
        t_alerte = Table(alerte_data, colWidths=["100%"])
        t_alerte.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_ALERTE),
            ("LINEBEFORE",    (0,0),(0,-1),  4, C_ALERTE_BORD),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("ROUNDEDCORNERS",[5]),
        ]))
        story.append(t_alerte)
        story.append(Spacer(1, 0.3*cm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 : SYNTHÈSE SECTORIELLE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(style_section(f"1. Synthèse du Secteur Bancaire Sénégalais — {annee_ref}"))

    col_db, client2 = get_collection()
    docs_all = list(col_db.find({"annee": annee_ref}, {"_id": 0}))
    client2.close()
    df_all = pd.DataFrame(docs_all) if docs_all else pd.DataFrame()

    nb_banques  = df_all["sigle"].nunique() if not df_all.empty else "N/D"
    total_bilan = df_all["bilan"].sum()     if "bilan" in df_all.columns else None
    total_pnb   = df_all["produit_net_bancaire"].sum() if "produit_net_bancaire" in df_all.columns else None

    annee_label = f"{annee} (données {annee_ref})" if annee_manquante else str(annee)
    synth_txt = (
        f"Le secteur bancaire sénégalais compte <b>{nb_banques} banques</b> actives "
        f"en {annee_ref}, représentant un total bilan de <b>{_fmt(total_bilan)}</b> "
        f"et un Produit Net Bancaire global de <b>{_fmt(total_pnb)}</b>. "
        f"La banque <b>{banque}</b> appartient au groupe <b>{row.get('groupe_bancaire','N/D')}</b>."
    )
    story.append(style_body(synth_txt))
    story.append(Spacer(1, 0.3*cm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 : INDICATEURS CLÉS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(style_section(f"2. Indicateurs Clés — {banque} ({annee_label})"))

    kpi_data = [
        ["INDICATEUR", "VALEUR", "INDICATEUR", "VALEUR"],
        ["Total Bilan",         _fmt(row.get("bilan")),
         "PNB",                 _fmt(row.get("produit_net_bancaire"))],
        ["Emploi (Crédits)",    _fmt(row.get("emploi")),
         "Ressources (Dépôts)", _fmt(row.get("ressources"))],
        ["Fonds Propres",       _fmt(row.get("fonds_propres")),
         "Résultat Net",        _fmt(row.get("resultat_net"))],
        ["Rés. Brut Exploit.",  _fmt(row.get("resultat_brut_exploitation")),
         "Charges Générales",   _fmt(row.get("charges_generales_exploitation"))],
        ["Coût du Risque",      _fmt(row.get("cout_du_risque")),
         "Impôts / Bénéfices",  _fmt(row.get("impots_benefices"))],
    ]

    t_kpi = Table(kpi_data, colWidths=["29%", "21%", "29%", "21%"])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1, 0), C_BLEU),
        ("TEXTCOLOR",     (0,0),(-1, 0), C_BLANC),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BLANC, C_FOND]),
        ("ALIGN",         (1,0),(1,-1),  "RIGHT"),
        ("ALIGN",         (3,0),(3,-1),  "RIGHT"),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 9),
        ("ROUNDEDCORNERS",[5]),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 0.35*cm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 : RATIOS FINANCIERS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(style_section("3. Analyse des Ratios Financiers"))

    ratio_data = [
        ["RATIO", "VALEUR", "NORME / RÉFÉRENCE", "INTERPRÉTATION"],
        ["ROA — Rendement des actifs",
         _pct(row.get("ratio_rendement_actifs")),
         "Secteur ~1–2 %",
         "Mesure l'efficacité à générer du profit"],
        ["ROE — Rentabilité fonds propres",
         _pct(row.get("ratio_rentabilite_capitaux")),
         "Secteur ~10–15 %",
         "Rendement pour les actionnaires"],
        ["Ratio de solvabilité",
         _pct(row.get("ratio_solvabilite")),
         "≥ 8 % (norme BCEAO)",
         "Solidité financière réglementaire"],
        ["Coeff. d'exploitation",
         _pct(row.get("coefficient_exploitation")),
         "< 65 % (optimal)",
         "Efficience opérationnelle"],
        ["Ratio liquidité (Emploi/Ress.)",
         _pct(row.get("ratio_emplois_ressources")),
         "< 100 % (prudentiel)",
         "Couverture des crédits par les dépôts"],
    ]

    t_rat = Table(ratio_data, colWidths=["30%", "15%", "22%", "33%"])
    t_rat.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1, 0), C_VERT),
        ("TEXTCOLOR",     (0,0),(-1, 0), C_BLANC),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BLANC, C_FOND]),
        ("ALIGN",         (1,0),(1,-1),  "CENTER"),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 9),
        ("ROUNDEDCORNERS",[5]),
    ]))
    story.append(t_rat)
    story.append(Spacer(1, 0.35*cm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 : ÉVOLUTION HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(style_section(
        f"4. Évolution Historique — {banque} "
        f"({', '.join(annees_dispo_str.split(', '))})"
    ))

    histo = df.sort_values("annee")[
        ["annee", "bilan", "produit_net_bancaire", "resultat_net", "fonds_propres"]
    ].dropna(subset=["bilan"])

    histo_rows = [["Année", "Bilan", "PNB", "Résultat Net", "Fonds Propres"]]
    for _, r in histo.iterrows():
        yr = int(r["annee"])
        histo_rows.append([
            str(yr),
            _fmt(r.get("bilan")),
            _fmt(r.get("produit_net_bancaire")),
            _fmt(r.get("resultat_net")),
            _fmt(r.get("fonds_propres")),
        ])

    t_histo = Table(histo_rows, colWidths=["10%", "22%", "22%", "23%", "23%"])
    t_histo.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1, 0), C_FONCE),
        ("TEXTCOLOR",     (0,0),(-1, 0), C_BLANC),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 7.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BLANC, C_FOND]),
        ("ALIGN",         (1,0),(-1,-1), "RIGHT"),
        ("ALIGN",         (0,0),(0,-1),  "CENTER"),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROUNDEDCORNERS",[5]),
    ]))
    story.append(t_histo)
    story.append(Spacer(1, 0.35*cm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 : POSITIONNEMENT CONCURRENTIEL
    # ══════════════════════════════════════════════════════════════════════════
    story.append(style_section(f"5. Positionnement Concurrentiel — Bilan {annee_ref}"))

    classmt = (
        df_all[["sigle", "bilan"]].dropna()
        .sort_values("bilan", ascending=False)
        .reset_index(drop=True)
    ) if not df_all.empty else pd.DataFrame(columns=["sigle", "bilan"])

    classmt.index += 1
    rang     = classmt[classmt["sigle"] == banque].index
    rang_txt = f"#{rang[0]}" if len(rang) > 0 else "N/D"
    nb_tot   = len(classmt)
    bilan_val = row.get("bilan")

    pos_txt = (
        f"La banque <b>{banque}</b> se positionne <b>{rang_txt} sur {nb_tot}</b> banques "
        f"en termes de total bilan en {annee_ref} ({_fmt(bilan_val)}). "
    )
    story.append(style_body(pos_txt))
    story.append(Spacer(1, 0.2*cm))

    top5 = classmt.head(5)
    top5_data = [["Rang", "Banque", "Bilan (M FCFA)"]]
    for idx, r2 in top5.iterrows():
        top5_data.append([f"#{idx}", r2["sigle"], f"{r2['bilan']:,.0f}"])

    t_top5 = Table(top5_data, colWidths=["15%", "50%", "35%"])
    t_top5.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1, 0), C_ORANGE),
        ("TEXTCOLOR",     (0,0),(-1, 0), C_BLANC),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BLANC, C_FOND]),
        ("ALIGN",         (2,0),(2,-1),  "RIGHT"),
        ("ALIGN",         (0,0),(0,-1),  "CENTER"),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 9),
        ("ROUNDEDCORNERS",[5]),
    ]))
    story.append(t_top5)

    # ══════════════════════════════════════════════════════════════════════════
    # PIED DE PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_GRIS))
    story.append(Spacer(1, 0.15*cm))

    note_annee = (
        f"⚠ Données affichées pour {annee_ref} (données {annee} non disponibles). · "
        if annee_manquante else ""
    )
    story.append(style_small(
        f"{note_annee}Rapport généré automatiquement · Banque : {banque} · "
        "Source : BCEAO & Base Sénégal · Dashboard DataViz M2 Big Data ISM · "
        "Les données proviennent de MongoDB (2015–2022).",
        color=C_GRIS
    ))

    # ── Build PDF ──────────────────────────────────────────────────────────────
    doc.build(story)
    pdf_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return pdf_b64