import streamlit as st
import pandas as pd
from collections import defaultdict

st.title("Répartition égalitaire bénévoles / enfants (étalée)")

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
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
        st.error(
            "Le CSV doit contenir EXACTEMENT les colonnes : Date, Horaires, Noms_dispos\n"
            f"Colonnes détectées : {df.columns.tolist()}"
        )
        st.stop()

    st.subheader("Aperçu du CSV")
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

    st.subheader("Enfants/Binômes détectés")
    st.write(noms_uniques)

    # =====================================================
    # 3️⃣ PARAMÈTRES
    # =====================================================
    min_par_date = st.slider("Nombre minimal de PERSONNES par créneau", 1, 10, 4)
    max_par_date = st.slider("Nombre maximal de PERSONNES par créneau", min_par_date, 10, max(5, min_par_date))

    # =====================================================
    # 4️⃣ DISPONIBILITÉS
    # =====================================================
    def compter_personnes(nom):
        return len(nom.split("/"))

    dispos_par_entite = {nom: 0 for nom in noms_uniques}
    for _, row in df.iterrows():
        if pd.notna(row["Noms_dispos"]):
            for n in str(row["Noms_dispos"]).split(separator):
                n = n.strip()
                if n in dispos_par_entite:
                    dispos_par_entite[n] += 1

    st.subheader("Disponibilités par enfant/binôme")
    st.write(dict(sorted(dispos_par_entite.items(), key=lambda x: x[1])))

    # =====================================================
    # 5️⃣ RÉPARTITION
    # =====================================================
    if st.button("Répartir les enfants"):

        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}
        ensemble = defaultdict(int)   # 👈 mémoire déjà ensemble
        DELAI_MINIMUM = 6

        mois_fr = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }

        def parse_dt(row):
            try:
                parts = str(row['Date']).lower().split()
                jour = int(parts[1])
                mois = mois_fr.get(parts[2], 1)
                heure = int(str(row['Horaires']).split('h')[0])
                return pd.Timestamp(2026, mois, jour, heure)
            except:
                return pd.Timestamp("1900-01-01")

        df_sorted = df.copy()
        df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        creneaux_info = []
        for _, row in df_sorted.iterrows():
            dispos = []
            if pd.notna(row["Noms_dispos"]):
                dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator)]
            creneaux_info.append({
                "cle": f"{row['Date']} | {row['Horaires']}",
                "dt": row["dt"],
                "dispos": dispos,
                "affectes": []
            })

        for creneau in creneaux_info:
            nb_personnes = 0
            candidats = []

            for n in creneau["dispos"]:
                if n in compteur:
                    distance = min([(creneau["dt"] - d).days for d in affectations[n]] + [999])
                    if distance >= DELAI_MINIMUM:
                        bonus = -100 if dispos_par_entite[n] < 5 else 0

                        # 🔸 pénalité déjà ensemble
                        penalite = 0
                        for a in creneau["affectes"]:
                            paire = tuple(sorted([n, a]))
                            penalite += ensemble[paire]

                        score = compteur[n] + bonus + penalite * 2
                        candidats.append((n, score, dispos_par_entite[n]))

            candidats.sort(key=lambda x: (x[1], x[2]))

            for nom, _, _ in candidats:
                p = compter_personnes(nom)
                if nb_personnes + p <= max_par_date:
                    creneau["affectes"].append(nom)

                    # 🔸 mise à jour mémoire ensemble
                    for autre in creneau["affectes"]:
                        if autre != nom:
                            paire = tuple(sorted([nom, autre]))
                            ensemble[paire] += 1

                    compteur[nom] += 1
                    affectations[nom].append(creneau["dt"])
                    nb_personnes += p

        # =====================================================
        # 6️⃣ AFFICHAGE
        # =====================================================
        st.subheader("Répartition finale")
        for c in creneaux_info:
            affichage = []
            for n in c["affectes"]:
                affichage.extend(n.split("/"))
            st.write(f"{c['cle']} : {', '.join(affichage)}")

        st.subheader("Occurrences par enfant/binôme")
        st.write(dict(sorted(compteur.items(), key=lambda x: x[1])))
