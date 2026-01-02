import streamlit as st
import pandas as pd
import random

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

    if not {"Date", "Horaires", "Noms_dispos"}.issubset(df.columns):
        st.error("Colonnes requises : Date ; Horaires ; Noms_dispos")
        st.stop()

    st.subheader("Aperçu du CSV")
    st.dataframe(df)

    # =====================================================
    # 2️⃣ EXTRACTION DES NOMS
    # =====================================================
    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        if pd.notna(cell)
        for n in str(cell).split(";")
        if n.strip()
    })

    if not noms_uniques:
        st.error("Aucun enfant détecté")
        st.stop()

    st.subheader("Enfants détectés")
    st.write(noms_uniques)

    # =====================================================
    # 3️⃣ PARAMÈTRES
    # =====================================================
    st.subheader("Paramètres des créneaux")

    min_par_date = st.slider("Minimum par créneau", 1, 10, 4)
    max_par_date = st.slider("Maximum par créneau", min_par_date, 10, max(5, min_par_date))

    # 👉 priorité à 4 enfants
    OBJECTIF_CRENEAU = max(min_par_date, min(4, max_par_date))

    # =====================================================
    # 4️⃣ OCCURRENCES MAX
    # =====================================================
    total_creaneaux = len(df)
    places_totales = total_creaneaux * max_par_date
    occ_recommandee = round(places_totales / len(noms_uniques))

    max_occ_global = st.number_input(
        "Occurrences max par enfant",
        min_value=1,
        max_value=total_creaneaux,
        value=occ_recommandee
    )

    # =====================================================
    # 5️⃣ BINÔMES
    # =====================================================
    st.subheader("Binômes")

    if "binomes" not in st.session_state:
        st.session_state.binomes = []

    col1, col2 = st.columns(2)
    with col1:
        enfant_a = st.selectbox("Enfant A", noms_uniques)
    with col2:
        enfant_b = st.selectbox("Enfant B", noms_uniques)

    if st.button("Ajouter le binôme") and enfant_a != enfant_b:
        if (enfant_a, enfant_b) not in st.session_state.binomes and (enfant_b, enfant_a) not in st.session_state.binomes:
            st.session_state.binomes.append((enfant_a, enfant_b))

    if st.session_state.binomes:
        for a, b in st.session_state.binomes:
            st.write(f"- {a} + {b}")

    binomes = st.session_state.binomes

    # =====================================================
    # 6️⃣ RÉPARTITION
    # =====================================================
    if st.button("Répartir les enfants"):

        repartition = {}
        compteur = {n: 0 for n in noms_uniques}
        affectations = {n: [] for n in noms_uniques}
        occ_par_mois = {n: {} for n in noms_uniques}

        DELAI_MIN = 7

        def parse_dt(row):
            return pd.to_datetime(
                f"{row['Date']} {row['Horaires']}",
                dayfirst=True,
                errors="coerce"
            )

        df_sorted = df.copy()
        df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        for _, row in df_sorted.iterrows():

            date = str(row["Date"]).strip()
            horaire = str(row["Horaires"]).strip()
            cle = f"{date} | {horaire}"

            repartition[cle] = []
            deja = set()

            dt = row["dt"]
            mois = dt.strftime("%Y-%m") if not pd.isna(dt) else "1900-01"

            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]

            # ---- BINÔMES
            for a, b in binomes:
                if (
                    a in dispos and b in dispos
                    and compteur[a] < max_occ_global
                    and compteur[b] < max_occ_global
                    and len(repartition[cle]) <= OBJECTIF_CRENEAU - 2
                ):
                    repartition[cle] += [a, b]
                    for n in (a, b):
                        compteur[n] += 1
                        affectations[n].append(dt)
                        occ_par_mois[n][mois] = occ_par_mois[n].get(mois, 0) + 1
                    deja.update([a, b])

            # ---- SOLOS (étalement mensuel prioritaire)
            scores = []
            for n in dispos:
                if n in deja or compteur[n] >= max_occ_global:
                    continue
                last = affectations[n]
                distance = min([(dt - d).days for d in last] + [999])
                mois_count = occ_par_mois[n].get(mois, 0)
                scores.append((n, mois_count, -distance, compteur[n]))

            scores.sort(key=lambda x: (x[1], x[2], x[3]))

            for n, _, _, _ in scores:
                if len(repartition[cle]) < OBJECTIF_CRENEAU:
                    repartition[cle].append(n)
                    compteur[n] += 1
                    affectations[n].append(dt)
                    occ_par_mois[n][mois] = occ_par_mois[n].get(mois, 0) + 1

        # =====================================================
        # 7️⃣ TRI DATE + HORAIRE
        # =====================================================
        def cle_tri(cle):
            date_str, heure_str = cle.split("|")
            d = pd.to_datetime(date_str.strip(), dayfirst=True, errors="coerce")
            h = pd.to_datetime(heure_str.strip(), format="%H:%M", errors="coerce")
            return (d, h)

        repartition = dict(sorted(repartition.items(), key=cle_tri))

        # =====================================================
        # 8️⃣ AFFICHAGE
        # =====================================================
        st.subheader("Répartition finale")

        for cle, enfants in repartition.items():
            st.write(
                f"{cle} : {', '.join(enfants) if enfants else 'Aucun'} "
                f"({len(enfants)} enfant(s))"
            )

        st.subheader("Occurrences par enfant")
        st.write(dict(sorted(compteur.items())))

        # =====================================================
        # 9️⃣ EXPORT CSV
        # =====================================================
        export_df = pd.DataFrame([
            {
                "Date_Horaire": cle,
                "Enfants_affectés": ";".join(enfants),
                "Places_restantes": max_par_date - len(enfants)
            }
            for cle, enfants in repartition.items()
        ])

        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")

        st.download_button(
            "Télécharger la répartition CSV",
            data=csv,
            file_name="repartition.csv",
            mime="text/csv"
        )
