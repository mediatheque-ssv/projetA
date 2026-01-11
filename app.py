import streamlit as st
import pandas as pd
import random
import io
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

<h1 style="
    color: #6D28D9; 
    font-size: 2.5em; 
    font-weight: 800; 
    text-align: center; 
    margin-bottom: 0.5em;
    font-variant: small-caps;
">
répartition mini-bénévoles
</h1>
""", unsafe_allow_html=True)

# =====================================================
# 1️⃣ TABLEAU ÉDITABLE DANS L’UI
# =====================================================
st.markdown("## 📋 Créneaux et disponibilités")

if "df_ui" not in st.session_state:
    st.session_state.df_ui = pd.DataFrame({
        "Date": [
            "mercredi 7 janvier",
            "mercredi 7 janvier",
            "samedi 10 janvier"
        ],
        "Horaires": ["10h", "15h", "10h"],
        "Noms_dispos": [
            "Alice;Bob",
            "Charlie/David;Emma",
            "Lucie;Paul"
        ]
    })

df = st.data_editor(
    st.session_state.df_ui,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Date": st.column_config.TextColumn(
            "Date",
            disabled=True
        ),
        "Horaires": st.column_config.TextColumn(
            "Horaires",
            disabled=True
        ),
        "Noms_dispos": st.column_config.TextColumn(
            "Noms_dispos",
            help="Séparer par ; — binôme avec /",
            disabled=False
        ),
    }
)

st.session_state.df_ui = df

if df.empty:
    st.warning("Ajoute au moins un créneau.")
    st.stop()

# =====================================================
# 2️⃣ EXTRACTION DES NOMS
# =====================================================
sample_cell = str(df["Noms_dispos"].iloc[0])
separator = "," if "," in sample_cell else ";"

noms_uniques = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    for n in str(cell).split(separator)
    if n.strip()
})

st.markdown("## 🧒 Enfants et binômes détectés")
df_noms = pd.DataFrame({
    "Enfant / binôme": noms_uniques,
    "Type": ["Binôme" if "/" in n else "Enfant seul" for n in noms_uniques]
})
st.dataframe(df_noms, use_container_width=True, hide_index=True)

# =====================================================
# 3️⃣ PARAMÈTRES
# =====================================================
st.markdown("## ⚙️ Paramètres")
col1, col2 = st.columns(2)
with col1:
    min_par_date = st.slider("Minimum par créneau", 1, 10, 4)
with col2:
    max_par_date = st.slider("Maximum par créneau", min_par_date, 10, max(5, min_par_date))

# =====================================================
# 4️⃣ DISPONIBILITÉS
# =====================================================
def compter_personnes(nom):
    return len(nom.split("/"))

dispos_par_entite = {n: 0 for n in noms_uniques}
for _, row in df.iterrows():
    for n in row["Noms_dispos"].split(separator):
        n = n.strip()
        if n in dispos_par_entite:
            dispos_par_entite[n] += 1

st.markdown("## 📊 Disponibilités")
st.dataframe(
    pd.DataFrame(dispos_par_entite.items(), columns=["Enfant / binôme", "Disponibilités"])
    .sort_values("Disponibilités"),
    use_container_width=True,
    hide_index=True
)

# =====================================================
# SESSION STATE
# =====================================================
for key in ["repartition", "output_excel", "output_pdf", "compteur"]:
    if key not in st.session_state:
        st.session_state[key] = None

# =====================================================
# 5️⃣ RÉPARTITION
# =====================================================
st.markdown("## ▶️ Lancer la répartition")

if st.button("Répartir"):
    compteur = {n: 0 for n in noms_uniques}
    affectations = {n: [] for n in noms_uniques}

    creneaux = []
    for _, row in df.iterrows():
        horaire = row["Horaires"]
        horaire_export = "10h - 11h" if horaire.startswith("10") else "15h - 16h"
        creneaux.append({
            "cle": f"{row['Date']} | {horaire_export}",
            "affectes": [],
            "dispos": [n.strip() for n in row["Noms_dispos"].split(separator)]
        })

    for c in creneaux:
        candidats = sorted(
            c["dispos"],
            key=lambda n: compteur[n] + random.random()
        )
        total = 0
        for n in candidats:
            if total + compter_personnes(n) <= max_par_date:
                c["affectes"].append(n)
                compteur[n] += 1
                total += compter_personnes(n)

    st.session_state.repartition = creneaux
    st.session_state.compteur = compteur

# =====================================================
# 6️⃣ AFFICHAGE
# =====================================================
if st.session_state.repartition:
    st.markdown("## 🧩 Répartition finale")
    for c in st.session_state.repartition:
        noms = []
        for e in c["affectes"]:
            noms.extend(e.split("/"))
        st.write(f"{c['cle']} : {', '.join(noms)}")

    st.markdown("## 🔁 Occurrences")
    st.dataframe(
        pd.DataFrame(
            st.session_state.compteur.items(),
            columns=["Enfant / binôme", "Occurrences"]
        ).sort_values("Occurrences"),
        use_container_width=True,
        hide_index=True
    )
