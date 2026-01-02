import streamlit as st
import pandas as pd
import random
from datetime import timedelta

st.title("Répartition égalitaire bénévoles / enfants (étalée)")

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if uploaded_file:

    # Lecture CSV
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    except Exception as e:
        st.error(f"Erreur de lecture du CSV : {e}")
        st.stop()

    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    if not set(["Date", "Horaires", "Noms_dispos"]).issubset(df.columns):
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
    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        if pd.notna(cell)
        for n in str(cell).split(";")
        if n.strip()
    })

    st.subheader("Enfants détectés")
    if not noms_uniques:
        st.warning("Aucun enfant détecté !")
        st.stop()

    st.write(noms_uniques)

    # =====================================================
    # 3️⃣ PARAMÈTRES DES CRÉNEAUX
    # =====================================================
    st.subheader("Paramètres des créneaux")

    min_par_date = st.slider(
        "Nombre minimal d'enfants par créneau",
        min_value=1, max_value=10, value=4
    )

    max_par_date = st.slider(
        "Nombre maximal d'enfants par créneau",
        min_value=min_par_date, max_value=10, value=max(5, min_par_date)
    )

    # =====================================================
    # 4️⃣ OCCURRENCES MAXIMALES GLOBALES
    # =====================================================
    total_creaneaux = len(df)
    places_totales = total_creaneaux * max_par_date
    occ_recommandee = round(places_totales / len(noms_uniques))

    st.info(
        f"Total créneaux : {total_creaneaux} — "
        f"Places totales : {places_totales} — "
        f"Occurrence idéale ≈ {occ_recommandee}"
    )

    max_occ_global = st.number_input(
        "Nombre maximal d'occurrences par enfant",
        min_value=1,
        max_value=total_creaneaux,
        value=occ_recommandee
    )

    # =====================================================
    # 5️⃣ BINÔMES
    # =====================================================
    st.subheader("Binômes à ne pas séparer")

    if "binomes" not in st.session_state:
        st.session_state.binomes = []

    col1, col2 = st.columns(2)
    with col1:
        enfant_a = st.selectbox("Enfant A", noms_uniques, key="a")
    with col2:
        enfant_b = st.selectbox("Enfant B", noms_uniques, key="b")

    if (
        enfant_a != enfant_b
        and st.button("Ajouter le binôme")
        and (enfant_a, enfant_b) not in st.session_state.binomes
        and (enfant_b, enfant_a) not in st.session_state.binomes
    ):
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

        DELAI_PREFERENTIEL = 14
        DELAI_MINIMUM = 7

        def parse_dt(row):
            try:
                return pd.to_datetime(
                    f"{row['Date']} {row['Horaires']}",
                    dayfirst=True,
                    errors="coerce"
                )
            except:
                return pd.NaT

        df_sorted = df.copy()
        df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        for _, row in df_sorted.iterrows():
            date = str(row["Date"]).strip()
            horaire = str(row["Horaires"]).strip()
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]

            cle = f"{date} | {horaire}"
            repartition[cle] = []
            date_dt = row["dt"] if not pd.isna(row["dt"]) else pd.to_datetime("1900-01-01")

            # BINÔMES
            for a, b in random.sample(binomes, len(binomes)):
                if (
                    a in dispos and b in dispos
                    and compteur[a] < max_occ_global
                    and compteur[b] < max_occ_global
                    and len(repartition[cle]) <= max_par_date - 2
                ):
                    da = min([(date_dt - d).days for d in affectations[a]] + [999])
                    db = min([(date_dt - d).days for d in affectations[b]] + [999])
                    if da >= DELAI_MINIMUM and db >= DELAI_MINIMUM:
                        repartition[cle] += [a, b]
                        compteur[a] += 1
                        compteur[b] += 1
                        affectations[a].append(date_dt)
                        affectations[b].append(date_dt)

            # SOLO
            solos = []
            for n in dispos:
                if n not in repartition[cle] and compteur[n] < max_occ_global:
                    d = min([(date_dt - d).days for d in affectations[n]] + [999])
                    solos.append((n, -d, compteur[n]))

            solos.sort(key=lambda x: (x[1], x[2]))

            for n, _, _ in solos:
                if len(repartition[cle]) < max_par_date:
                    repartition[cle].append(n)
                    compteur[n] += 1
                    affectations[n].append(date_dt)

            # Complément min
            for n in noms_uniques:
                if len(repartition[cle]) >= min_par_date:
                    break
                if n not in repartition[cle] and compteur[n] < max_occ_global:
                    repartition[cle].append(n)
                    compteur[n] += 1
                    affectations[n].append(date_dt)

        # =====================================================
        # 7️⃣ TRI ROBUSTE
        # =====================================================
        def cle_tri(cle):
            cle = str(cle)
            parts = cle.split("|", 1)

            date_str = parts[0].strip()
            heure_str = parts[1].strip() if len(parts) == 2 else "00:00"

            date_dt = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
            if pd.isna(date_dt):
                date_dt = pd.to_datetime("1900-01-01")

            heure_dt = pd.to_datetime(heure_str, format="%H:%M", errors="coerce")
            if pd.isna(heure_dt):
                heure_dt = pd.to_datetime("00:00", format="%H:%M")

            return (date_dt, heure_dt)

        repartition = dict(sorted(repartition.items(), key=cle_tri))

        # =====================================================
        # 8️⃣ AFFICHAGE
        # =====================================================
        st.subheader("Répartition finale")
        for cle, enfants in repartition.items():
            st.write(
                f"{cle} : "
                f"{', '.join(enfants) if enfants else 'Aucun'} "
                f"({max_par_date - len(enfants)} place(s) restante(s))"
            )

        st.subheader("Occurrences par enfant")
        st.write(dict(sorted(compteur.items())))

        # =====================================================
        # 9️⃣ EXPORT
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
