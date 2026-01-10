import streamlit as st
import pandas as pd
import random

st.set_page_config(
    page_title="Répartition mini-bénévoles",
    layout="wide"
)

st.title("Répartition mini-bénévoles")

# =====================================================
# 🎨 STYLE
# =====================================================
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

# =====================================================
# 1️⃣ IMPORT CSV
# =====================================================
st.markdown("## 📂 Import du CSV")
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if not uploaded_file:
    st.stop()

df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

# =====================================================
# 2️⃣ EXTRACTION DES NOMS
# =====================================================
sample_cell = str(df["Noms_dispos"].iloc[0])
separator = "," if "," in sample_cell else ";"

noms_uniques = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    if pd.notna(cell)
    for n in str(cell).split(separator)
    if n.strip()
})

st.markdown("## 🧒 Enfants et binômes détectés")
st.dataframe(
    pd.DataFrame({
        "Enfant / binôme": noms_uniques,
        "Type": ["Binôme" if "/" in n else "Enfant seul" for n in noms_uniques]
    }),
    use_container_width=True,
    hide_index=True
)

# =====================================================
# 3️⃣ PARAMÈTRES
# =====================================================
st.markdown("## ⚙️ Paramètres")

col1, col2 = st.columns(2)
with col1:
    min_par_date = st.slider("👥 Minimum par créneau", 1, 10, 4)
with col2:
    max_par_date = st.slider("👥 Maximum par créneau", min_par_date, 10, 6)

col3, col4 = st.columns(2)
with col3:
    min_occ_personne = st.slider("🔽 Minimum d'occurrences", 0, 10, 3)
with col4:
    max_occ_personne = st.slider("🔼 Maximum d'occurrences", min_occ_personne, 20, 5)

# =====================================================
# 4️⃣ OUTILS
# =====================================================
def compter_personnes(nom):
    return len(nom.split("/"))

mois_fr = {
    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
}

def parse_dt(row):
    try:
        parts = str(row["Date"]).lower().split()
        jour = int(parts[1])
        mois = mois_fr.get(parts[2], 1)
        heure = int(str(row["Horaires"]).split("h")[0])
        return pd.Timestamp(2026, mois, jour, heure)
    except:
        return pd.Timestamp("1900-01-01")

# =====================================================
# 5️⃣ PRÉPARATION DES CRÉNEAUX
# =====================================================
df_sorted = df.copy()
df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
df_sorted = df_sorted.sort_values("dt")

creneaux = []
for _, row in df_sorted.iterrows():
    dispos = [
        n.strip() for n in str(row["Noms_dispos"]).split(separator)
        if n.strip() in noms_uniques
    ]
    creneaux.append({
        "cle": f"{row['Date']} | {row['Horaires']}",
        "dt": row["dt"],
        "dispos": dispos,
        "affectes": []
    })

# =====================================================
# 6️⃣ RÉPARTITION
# =====================================================
if st.button("▶️ Lancer la répartition"):

    compteur = {n: 0 for n in noms_uniques}
    affectations = {n: [] for n in noms_uniques}
    DELAI_MINIMUM = 6

    # -------------------------------------------------
    # 🥇 PHASE 1 — GARANTIR LES MINIMUMS (SANS ALÉA)
    # -------------------------------------------------
    impossibles = []

    for nom in noms_uniques:
        while compteur[nom] < min_occ_personne:
            placé = False

            for c in creneaux:
                if nom not in c["dispos"] or nom in c["affectes"]:
                    continue

                nb_pers = sum(compter_personnes(x) for x in c["affectes"])
                if nb_pers + compter_personnes(nom) > max_par_date:
                    continue

                dist = min([(c["dt"] - d).days for d in affectations[nom]] + [999])
                if dist < DELAI_MINIMUM:
                    continue

                c["affectes"].append(nom)
                compteur[nom] += 1
                affectations[nom].append(c["dt"])
                placé = True
                break

            if not placé:
                impossibles.append(nom)
                break

    # -------------------------------------------------
    # 🥈 PHASE 2 — COMPLÉTER (AVEC ALÉATOIRE)
    # -------------------------------------------------
    for c in creneaux:
        nb_pers = sum(compter_personnes(x) for x in c["affectes"])

        candidats = [
            n for n in c["dispos"]
            if n not in c["affectes"]
            and compteur[n] < max_occ_personne
        ]

        random.shuffle(candidats)

        for n in candidats:
            if nb_pers + compter_personnes(n) <= max_par_date:
                c["affectes"].append(n)
                compteur[n] += 1
                affectations[n].append(c["dt"])
                nb_pers += compter_personnes(n)

    # =====================================================
    # 7️⃣ AFFICHAGE
    # =====================================================
    st.markdown("## 🧩 Répartition finale")

    for c in creneaux:
        enfants = []
        for e in c["affectes"]:
            enfants.extend(e.split("/"))

        st.write(
            f"{c['cle']} : {', '.join(enfants) if enfants else 'Aucun'}"
        )

    st.markdown("## 🔁 Occurrences par enfant / binôme")
    st.dataframe(
        pd.DataFrame(
            compteur.items(),
            columns=["Enfant / binôme", "Occurrences"]
        ).sort_values("Occurrences"),
        use_container_width=True,
        hide_index=True
    )

    if impossibles:
        st.warning(
            "⚠️ Minimum impossible à garantir pour : "
            + ", ".join(sorted(set(impossibles)))
            + "\n➡️ Contraintes incompatibles (disponibilités / délais / capacités)."
        )
