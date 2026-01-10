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
hr {
    border: none;
    height: 2px;
    background-color: #DDD6FE;
    margin: 1.5em 0;
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
    min_par_date = st.slider("👥 Minimum par créneau", 1, 10, 4)
with col2:
    max_par_date = st.slider("👥 Maximum par créneau", min_par_date, 10, 6)

col3, col4 = st.columns(2)
with col3:
    min_occ_personne = st.slider("🔽 Minimum d'occurrences par enfant / binôme", 0, 10, 3)
with col4:
    max_occ_personne = st.slider("🔼 Maximum d'occurrences par enfant / binôme", min_occ_personne, 20, 5)

# =====================================================
# 4️⃣ DISPONIBILITÉS
# =====================================================
def compter_personnes(nom):
    return len(nom.split("/"))

dispos_par_entite = {nom: 0 for nom in noms_uniques}
for _, row in df.iterrows():
    for n in str(row["Noms_dispos"]).split(separator):
        n = n.strip()
        if n in dispos_par_entite:
            dispos_par_entite[n] += 1

# =====================================================
# 5️⃣ FONCTION DE RÉPARTITION (🔧 clé)
# =====================================================
def lancer_repartition():
    compteur = {nom: 0 for nom in noms_uniques}
    affectations = {nom: [] for nom in noms_uniques}

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

    df_sorted = df.copy()
    df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
    df_sorted = df_sorted.sort_values("dt")

    creneaux = []
    for _, row in df_sorted.iterrows():
        dispos = [
            n.strip() for n in str(row["Noms_dispos"]).split(separator)
            if n.strip() in compteur
        ]
        creneaux.append({
            "cle": f"{row['Date']} | {row['Horaires']}",
            "dt": row["dt"],
            "dispos": dispos,
            "affectes": []
        })

    DELAI_MINIMUM = 6

    # ---- Passage principal
    for c in creneaux:
        nb_pers = 0
        candidats = []

        for n in c["dispos"]:
            if compteur[n] >= max_occ_personne:
                continue
            dist = min([(c["dt"] - d).days for d in affectations[n]] + [999])
            if dist >= DELAI_MINIMUM:
                score = compteur[n] + random.uniform(-0.5, 0.5)
                candidats.append((n, score))

        candidats.sort(key=lambda x: x[1])

        for n, _ in candidats:
            if nb_pers + compter_personnes(n) <= max_par_date:
                c["affectes"].append(n)
                compteur[n] += 1
                affectations[n].append(c["dt"])
                nb_pers += compter_personnes(n)

    # ---- Rattrapage minimum
    for n in noms_uniques:
        while (
            compteur[n] < min_occ_personne
            and compteur[n] < max_occ_personne
            and dispos_par_entite[n] >= min_occ_personne
        ):
            ajouté = False
            for c in creneaux:
                if n in c["dispos"] and n not in c["affectes"]:
                    nb_pers = sum(compter_personnes(x) for x in c["affectes"])
                    if nb_pers + compter_personnes(n) <= max_par_date:
                        c["affectes"].append(n)
                        compteur[n] += 1
                        affectations[n].append(c["dt"])
                        ajouté = True
                        break
            if not ajouté:
                break

    return creneaux, compteur

# =====================================================
# 6️⃣ MULTI-TENTATIVES (🔧 correction majeure)
# =====================================================
if st.button("▶️ Lancer la répartition"):
    meilleure = None
    meilleur_compteur = None

    for _ in range(30):
        creneaux, compteur = lancer_repartition()
        non_ok = [
            n for n, c in compteur.items()
            if c < min_occ_personne and dispos_par_entite[n] >= min_occ_personne
        ]
        if not non_ok:
            meilleure = creneaux
            meilleur_compteur = compteur
            break
        if meilleure is None:
            meilleure = creneaux
            meilleur_compteur = compteur

    # =====================================================
    # 7️⃣ AFFICHAGE
    # =====================================================
    st.markdown("## 🧩 Répartition finale")
    for c in meilleure:
        enfants = []
        for e in c["affectes"]:
            enfants.extend(e.split("/"))
        st.write(f"{c['cle']} : {', '.join(enfants) if enfants else 'Aucun'}")

    st.markdown("## 🔁 Occurrences par enfant / binôme")
    st.dataframe(
        pd.DataFrame(
            meilleur_compteur.items(),
            columns=["Enfant / binôme", "Occurrences"]
        ).sort_values("Occurrences"),
        use_container_width=True,
        hide_index=True
    )

    non_ok = [
        n for n, c in meilleur_compteur.items()
        if c < min_occ_personne and dispos_par_entite[n] >= min_occ_personne
    ]
    if non_ok:
        st.warning(
            "⚠️ Le minimum n’a pas pu être atteint pour : "
            + ", ".join(non_ok)
            + "\n➡️ Une répartition optimale a été choisie malgré tout."
        )
