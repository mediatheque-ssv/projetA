import streamlit as st
import pandas as pd
import random
import io
import re

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
.stMarkdown p { font-size: 14px; }
.stButton>button {
    background-color: #6D28D9;
    color: white;
    border-radius: 12px;
    padding: 0.6em 1.2em;
    font-size: 1.05em;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #5B21B6;
    color: white;
}
</style>
<h1 style="color:#6D28D9;text-align:center;font-variant:small-caps;">
répartition mini-bénévoles
</h1>
""", unsafe_allow_html=True)

# =====================================================
# TABLEAU ÉDITABLE
# =====================================================
st.markdown("## 📝 Saisie des créneaux")

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["Date", "Horaires", "Noms_dispos"]
    )

edited_df = st.data_editor(
    st.session_state.data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Date": st.column_config.TextColumn("Date"),
        "Horaires": st.column_config.TextColumn("Horaires", help="10h ou 15h"),
        "Noms_dispos": st.column_config.TextColumn(
            "Noms_dispos",
            help="Séparateur : ;  |  Binôme : /  |  PAS d'espace"
        ),
    }
)

st.session_state.data = edited_df

# =====================================================
# VALIDATION
# =====================================================
jours = "lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche"
mois = "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"

date_regex = re.compile(rf"^({jours})\s+\d{{1,2}}\s+({mois})$", re.IGNORECASE)
horaire_regex = re.compile(r"^(10h|15h)$")

erreurs = []

for idx, row in edited_df.iterrows():
    ligne = idx + 1

    date = str(row["Date"]).strip()
    if not date_regex.match(date):
        erreurs.append(f"Ligne {ligne} – Date invalide : {date}")

    horaire = str(row["Horaires"]).strip()
    if not horaire_regex.match(horaire):
        erreurs.append(f"Ligne {ligne} – Horaire invalide : {horaire}")

    noms = str(row["Noms_dispos"]).strip()
    if not noms:
        erreurs.append(f"Ligne {ligne} – Aucun nom")
    elif " " in noms:
        erreurs.append(f"Ligne {ligne} – Espaces interdits dans les noms")
    elif "," in noms:
        erreurs.append(f"Ligne {ligne} – Virgules interdites")
    elif ";;" in noms:
        erreurs.append(f"Ligne {ligne} – Séparateurs multiples (;;)")
    elif noms.startswith(";") or noms.endswith(";"):
        erreurs.append(f"Ligne {ligne} – Séparateur mal placé")

if erreurs:
    st.error("⚠️ Erreurs détectées")
    for e in erreurs:
        st.write("•", e)
    st.stop()
else:
    st.success("✅ Données valides")

# =====================================================
# PARAMÈTRES
# =====================================================
col1, col2 = st.columns(2)
with col1:
    min_par_date = st.slider("Minimum par créneau", 1, 10, 4)
with col2:
    max_par_date = st.slider("Maximum par créneau", min_par_date, 10, max(5, min_par_date))

# =====================================================
# RÉPARTITION
# =====================================================
if "repartition" not in st.session_state:
    st.session_state.repartition = None
    st.session_state.output_excel = None
    st.session_state.output_pdf = None

if st.button("Répartir les enfants"):

    df = edited_df.copy()
    separator = ";"

    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        for n in str(cell).split(separator)
        if n.strip()
    })

    dispos_par_entite = {n: 0 for n in noms_uniques}
    for cell in df["Noms_dispos"]:
        for n in cell.split(separator):
            dispos_par_entite[n] += 1

    def compter_personnes(n):
        return len(n.split("/"))

    compteur = {n: 0 for n in noms_uniques}
    affectations = {n: [] for n in noms_uniques}

    creneaux = []
    for _, r in df.iterrows():
        horaire_export = "10h - 11h" if r["Horaires"] == "10h" else "15h - 16h"
        creneaux.append({
            "cle": f"{r['Date']} | {horaire_export}",
            "dispos": r["Noms_dispos"].split(separator),
            "affectes": []
        })

    for c in creneaux:
        for nom in sorted(c["dispos"], key=lambda x: compteur[x]):
            if sum(compter_personnes(n) for n in c["affectes"]) + compter_personnes(nom) <= max_par_date:
                c["affectes"].append(nom)
                compteur[nom] += 1

    st.session_state.repartition = creneaux

    # =====================================================
    # OCCURRENCES
    # =====================================================
    st.markdown("## 🔁 Occurrences")
    df_occ = pd.DataFrame(compteur.items(), columns=["Enfant / binôme", "Occurrences"])
    st.dataframe(df_occ, use_container_width=True, hide_index=True)

    # =====================================================
    # EXPORT DATAFRAME
    # =====================================================
    export_df = pd.DataFrame([
        {
            "DATE": c["cle"].split(" | ")[0],
            "HORAIRES": c["cle"].split(" | ")[1],
            "NOMS DES MINI-BÉNÉVOLES": ", ".join(n for e in c["affectes"] for n in e.split("/"))
        }
        for c in creneaux
    ])

    # EXCEL
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Répartition")
    st.session_state.output_excel = output_excel

    # PDF (1 page auto)
    output_pdf = io.BytesIO()
    c = canvas.Canvas(output_pdf, pagesize=A4)
    width, height = A4

    data = [export_df.columns.tolist()] + export_df.values.tolist()
    row_height = min(35, (height - 100) / len(data))

    table = Table(data, colWidths=[120, 90, 280], rowHeights=row_height)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#F2CEEF")),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, 30, height - 50 - row_height * len(data))
    c.save()

    st.session_state.output_pdf = output_pdf

# =====================================================
# AFFICHAGE FINAL + BOUTONS
# =====================================================
if st.session_state.repartition:
    st.markdown("## 🧩 Répartition finale")
    for c in st.session_state.repartition:
        noms = ", ".join(n for e in c["affectes"] for n in e.split("/"))
        st.write(f"{c['cle']} : {noms}")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Télécharger Excel",
            st.session_state.output_excel.getvalue(),
            "repartition.xlsx"
        )
    with col2:
        st.download_button(
            "Télécharger PDF",
            st.session_state.output_pdf.getvalue(),
            "repartition.pdf"
        )
