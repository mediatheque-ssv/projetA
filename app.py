import streamlit as st
import pandas as pd
import random

st.title("Répartition mini-bénévoles")

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
    color: white;
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
# 1️⃣ IMPORT DU CSV
# =====================================================
st.markdown("## 📂 Import du CSV")
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    except Exception as e:
        st.error(f"Erreur de lecture du CSV : {e}")
        st.stop()

    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    if not set(["Date", "Horaires", "Noms_dispos"]).issubset(set(df.columns)):
        st.error("Le CSV doit contenir EXACTEMENT les colonnes : Date, Horaires, Noms_dispos")
        st.stop()

    st.dataframe(df)

    # =====================================================
    # 2️⃣ EXTRACTION DES NOMS
    # =====================================================
    sample_cell = str(df["Noms_dispos"].iloc[0]) if len(df) > 0 else ""
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
        min_par_date = st.slider("Minimum par créneau", 1, 10, 4)
    with col2:
        max_par_date = st.slider("Maximum par créneau", min_par_date, 10, max(5, min_par_date))

    col3, col4 = st.columns(2)
    with col3:
        min_occ_personne = st.slider("Minimum d'occurrences par enfant/binôme", 0, 10, 3)
    with col4:
        max_occ_personne = st.slider("Maximum d'occurrences par enfant/binôme", min_occ_personne, 20, 5)

    # =====================================================
    # 4️⃣ DISPONIBILITÉS
    # =====================================================
    def compter_personnes(nom):
        return len(nom.split("/"))

    dispos_par_entite = {nom: 0 for nom in noms_uniques}
    for _, row in df.iterrows():
        dispos = str(row["Noms_dispos"]).split(separator)
        for n in dispos:
            n = n.strip()
            if n in dispos_par_entite:
                dispos_par_entite[n] += 1

    # =====================================================
    # 5️⃣ RÉPARTITION
    # =====================================================
    if st.button("Répartir les enfants"):

        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}
        DELAI_MINIMUM = 6

        mois_fr = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }

        def parse_dt(row):
            try:
                d = row["Date"].lower().split()
                jour = int(d[1])
                mois = mois_fr[d[2]]
                heure = int(row["Horaires"].replace("h", "").split(":")[0])
                return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure)
            except:
                return pd.Timestamp("1900-01-01")

        df_sorted = df.copy()
        df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        creneaux_info = []
        for _, row in df_sorted.iterrows():
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator) if n.strip()]
            dispos = [n for n in dispos if n in compteur]

            creneaux_info.append({
                "cle": f"{row['Date']} | {row['Horaires']}",
                "dt": row["dt"],
                "dispos": dispos,
                "affectes": []
            })

        # ---- PASSAGE PRINCIPAL
        for creneau in creneaux_info:
            nb_pers = 0
            candidats = []

            for n in creneau["dispos"]:
                if compteur[n] >= max_occ_personne:
                    continue

                dist = min([(creneau["dt"] - d).days for d in affectations[n]] + [999])
                if dist >= DELAI_MINIMUM:
                    bonus = -100 if dispos_par_entite[n] < 5 else 0
                    candidats.append((n, compteur[n] + bonus + random.random()))

            candidats.sort(key=lambda x: x[1])

            for nom, _ in candidats:
                if nb_pers + compter_personnes(nom) <= max_par_date:
                    creneau["affectes"].append(nom)
                    compteur[nom] += 1
                    affectations[nom].append(creneau["dt"])
                    nb_pers += compter_personnes(nom)

        # ---- RATTRAPAGE DU MINIMUM (CORRIGÉ)
        for nom in noms_uniques:
            while (
                compteur[nom] < min_occ_personne
                and compteur[nom] < max_occ_personne
                and dispos_par_entite[nom] >= min_occ_personne
            ):
                ajouté = False
                for creneau in creneaux_info:
                    if nom in creneau["dispos"] and nom not in creneau["affectes"]:
                        nb_pers = sum(compter_personnes(n) for n in creneau["affectes"])
                        if nb_pers + compter_personnes(nom) <= max_par_date:
                            creneau["affectes"].append(nom)
                            compteur[nom] += 1
                            affectations[nom].append(creneau["dt"])
                            ajouté = True
                            break
                if not ajouté:
                    break

        # =====================================================
        # 6️⃣ ALERTES MIN NON RESPECTÉ
        # =====================================================
        non_respect_min = [
            nom for nom, c in compteur.items()
            if c < min_occ_personne and dispos_par_entite[nom] >= min_occ_personne
        ]

        if non_respect_min:
            st.warning(
                "⚠️ Minimum d'occurrences impossible à respecter pour :\n\n"
                + ", ".join(non_respect_min)
                + "\n\n➡️ Contraintes trop fortes (créneaux pleins, délai, binômes…)."
            )

        # =====================================================
        # 7️⃣ AFFICHAGE
        # =====================================================
        st.markdown("## 🧩 Répartition finale")
        for c in creneaux_info:
            enfants = []
            for e in c["affectes"]:
                enfants.extend(e.split("/"))
            st.write(f"{c['cle']} : {', '.join(enfants) if enfants else 'Aucun'}")

        df_occ = pd.DataFrame(compteur.items(), columns=["Enfant / binôme", "Occurrences"])
        st.dataframe(df_occ.sort_values("Occurrences"), use_container_width=True)
