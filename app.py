import streamlit as st
import pandas as pd
import random
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# ===========================
# STYLE
# ===========================
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
}
hr { border: none; height: 2px; background-color: #DDD6FE; margin: 1.5em 0; }
</style>

<h1 style="
    color:#6D28D9;
    font-size:2.5em;
    font-weight:800;
    text-align:center;
    font-variant:small-caps;">
répartition mini-bénévoles
</h1>
""", unsafe_allow_html=True)

# ===========================
# IMPORT CSV
# ===========================
st.markdown("## 📂 Import du CSV")
uploaded_file = st.file_uploader("Importer le CSV", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    if not {"Date","Horaires","Noms_dispos"}.issubset(df.columns):
        st.error("Colonnes attendues : Date ; Horaires ; Noms_dispos")
        st.stop()

    separator = ";"

    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"].dropna()
        for n in str(cell).split(separator)
        if n.strip()
    })

    # ===========================
    # PARAMÈTRES
    # ===========================
    st.markdown("## ⚙️ Paramètres des créneaux")
    col1, col2 = st.columns(2)
    with col1:
        min_par_date = st.slider("Minimum", 1, 10, 4)
    with col2:
        max_par_date = st.slider("Maximum", min_par_date, 10, max(5, min_par_date))

    # ===========================
    # SESSION STATE
    # ===========================
    for key in ["repartition","compteur","output_excel","output_pdf"]:
        if key not in st.session_state:
            st.session_state[key] = None

    # ===========================
    # FONCTION DE RÉPARTITION
    # ===========================
    def lancer_repartition():
        compteur = {n:0 for n in noms_uniques}
        affectations = {n:[] for n in noms_uniques}
        creneaux = []

        for _, row in df.iterrows():
            horaire = row["Horaires"]
            horaire_export = "10h - 11h" if horaire.startswith("10") else "15h - 16h"
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]
            creneaux.append({
                "cle": f"{row['Date']} | {horaire_export}",
                "dispos": dispos,
                "affectes":[]
            })

        for c in creneaux:
            random.shuffle(c["dispos"])
            for n in c["dispos"]:
                if compteur[n] < max_par_date:
                    c["affectes"].append(n)
                    compteur[n] += 1
                    if len(c["affectes"]) >= max_par_date:
                        break

        st.session_state.repartition = creneaux
        st.session_state.compteur = compteur

        # ===== EXCEL =====
        export_df = pd.DataFrame([{
            "DATE": c["cle"].split(" | ")[0],
            "HORAIRES": c["cle"].split(" | ")[1],
            "NOMS DES MINI-BÉNÉVOLES": ", ".join(c["affectes"])
        } for c in creneaux])

        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
            export_df.to_excel(writer, index=False)
        st.session_state.output_excel = output_excel

        # ===== PDF =====
        output_pdf = io.BytesIO()
        c = canvas.Canvas(output_pdf, pagesize=A4)
        width, height = A4

        data = [["DATE","HORAIRES","NOMS DES MINI-BÉNÉVOLES"]] + export_df.values.tolist()
        row_height = (height-100)/len(data)

        table = Table(data, colWidths=[120,80,300], rowHeights=row_height)
        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#F2CEEF")),
            ('GRID',(0,0),(-1,-1),1,colors.black),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')
        ]))
        table.wrapOn(c,width,height)
        table.drawOn(c,30,height-50-row_height*len(data))
        c.save()
        output_pdf.seek(0)
        st.session_state.output_pdf = output_pdf

    # ===========================
    # BOUTONS
    # ===========================
    colA, colB = st.columns(2)

    with colA:
        if st.button("▶️ Répartir les enfants"):
            lancer_repartition()

    with colB:
        if st.session_state.repartition and st.button("🔄 Relancer avec un autre tirage"):
            lancer_repartition()

# ===========================
# AFFICHAGE
# ===========================
if st.session_state.repartition:
    st.markdown("## 🧩 Répartition finale")
    for c in st.session_state.repartition:
        st.write(f"{c['cle']} : {', '.join(c['affectes'])}")

    st.markdown("## 🔁 Occurrences")
    df_occ = pd.DataFrame(
        st.session_state.compteur.items(),
        columns=["Enfant / binôme","Occurrences"]
    )
    st.dataframe(df_occ, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Télécharger Excel",
            st.session_state.output_excel.getvalue(),
            "repartition.xlsx")
    with col2:
        st.download_button("Télécharger PDF",
            st.session_state.output_pdf.getvalue(),
            "repartition.pdf")
