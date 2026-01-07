import streamlit as st
import pandas as pd

st.title("Répartition égalitaire bénévoles / enfants (étalée)")

uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if uploaded_file:

    df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    st.dataframe(df)

    # =====================================================
    # EXTRACTION DES NOMS
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

    # =====================================================
    # PARAMÈTRES
    # =====================================================
    min_par_date = st.slider("Min par créneau", 1, 10, 4)
    max_par_date = st.slider("Max par créneau", min_par_date, 10, 5)

    # =====================================================
    # DISPOS DE BASE
    # =====================================================
    dispos_par_enfant = {nom: 0 for nom in noms_uniques}
    for _, row in df.iterrows():
        dispos = str(row["Noms_dispos"]).split(separator)
        for n in dispos:
            n = n.strip()
            if n in dispos_par_enfant:
                dispos_par_enfant[n] += 1

    # =====================================================
    # BINÔMES
    # =====================================================
    if "binomes" not in st.session_state:
        st.session_state.binomes = []

    col1, col2 = st.columns(2)
    with col1:
        a = st.selectbox("Enfant A", noms_uniques)
    with col2:
        b = st.selectbox("Enfant B", noms_uniques)

    if st.button("Ajouter le binôme") and a != b:
        if (a, b) not in st.session_state.binomes and (b, a) not in st.session_state.binomes:
            st.session_state.binomes.append((a, b))

    binomes = st.session_state.binomes
    st.write("Binômes :", binomes)

    # =====================================================
    # CALCUL DES DISPOS COMMUNES DES BINÔMES
    # =====================================================
    binomes_actifs = {}
    for a, b in binomes:
        commun = 0
        for _, row in df.iterrows():
            dispos = str(row["Noms_dispos"]).split(separator)
            dispos = [x.strip() for x in dispos]
            if a in dispos and b in dispos:
                commun += 1
        if commun > 0:
            binomes_actifs[(a, b)] = commun

    # =====================================================
    # RÉPARTITION
    # =====================================================
    compteur = {n: 0 for n in noms_uniques}
    affectations = {n: [] for n in noms_uniques}
    DELAI_MINIMUM = 6

    # Parsing date
    mois_fr = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
    }

    def parse_dt(row):
        parts = str(row['Date']).lower().split()
        jour = int(parts[1])
        mois = mois_fr.get(parts[2], 1)
        heure = int(str(row['Horaires']).split("h")[0])
        return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure)

    df["dt"] = df.apply(parse_dt, axis=1)
    df = df.sort_values("dt")

    creneaux = []
    for _, row in df.iterrows():
        dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator)]
        creneaux.append({
            "cle": f"{row['Date']} | {row['Horaires']}",
            "dt": row["dt"],
            "dispos": dispos,
            "affectes": []
        })

    if st.button("Répartir"):

        for _ in range(50):

            progress = 0

            for c in creneaux:

                if len(c["affectes"]) >= max_par_date:
                    continue

                # ===== BINÔMES =====
                candidats_binomes = []
                for (a, b), reste in binomes_actifs.items():
                    if reste <= 0:
                        continue
                    if a in c["dispos"] and b in c["dispos"]:
                        if a not in c["affectes"] and b not in c["affectes"]:
                            if len(c["affectes"]) <= max_par_date - 2:
                                score = compteur[a]
                                candidats_binomes.append((a, b, score, reste))

                candidats_binomes.sort(key=lambda x: (x[2], x[3]))

                if candidats_binomes:
                    a, b, _, _ = candidats_binomes[0]
                    c["affectes"].extend([a, b])
                    compteur[a] += 1
                    compteur[b] += 1
                    affectations[a].append(c["dt"])
                    affectations[b].append(c["dt"])
                    binomes_actifs[(a, b)] -= 1
                    progress += 2
                    continue

                # ===== SOLO =====
                solos = []
                for n in c["dispos"]:
                    if n not in c["affectes"]:
                        solos.append((n, compteur[n], dispos_par_enfant[n]))

                solos.sort(key=lambda x: (x[1], x[2]))

                for n, _, _ in solos:
                    if len(c["affectes"]) < max_par_date:
                        c["affectes"].append(n)
                        compteur[n] += 1
                        affectations[n].append(c["dt"])
                        progress += 1

            if progress == 0:
                break

        # =====================================================
        # AFFICHAGE
        # =====================================================
        for c in creneaux:
            st.write(
                f"{c['cle']} : {', '.join(c['affectes'])} "
                f"({max_par_date - len(c['affectes'])} place(s))"
            )

        st.subheader("Occurrences")
        st.write(dict(sorted(compteur.items(), key=lambda x: x[1])))
