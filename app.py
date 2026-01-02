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
    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        if pd.notna(cell)
        for n in str(cell).split(";")
        if n.strip()
    })

    st.subheader("Enfants détectés")
    if noms_uniques:
        st.write(noms_uniques)
    else:
        st.warning("Aucun enfant détecté ! Vérifie le CSV et le séparateur ';'")
        st.stop()

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
    st.info(f"Total créneaux : {total_creaneaux}, Places totales : {places_totales} → Occurrence idéale par enfant ≈ {occ_recommandee}")

    max_occ_global = st.number_input(
        "Nombre maximal d'occurrences par enfant (pour tous)",
        min_value=1,
        max_value=total_creaneaux,
        value=occ_recommandee
    )

    # =====================================================
    # 5️⃣ BINÔMES (INTERFACE)
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
        st.write("Binômes définis :")
        for a, b in st.session_state.binomes:
            st.write(f"- {a} + {b}")

    binomes = st.session_state.binomes

    # =====================================================
    # 6️⃣ RÉPARTITION ÉGALITAIRE AVEC ESPACEMENT ET MIN PAR CRÉNEAU
    # =====================================================
    if st.button("Répartir les enfants"):

        repartition = {}
        compteur = {nom: 0 for nom in noms_uniques}
        deja_affectes_par_date = {}
        affectations = {nom: [] for nom in noms_uniques}  # stocke les datetimes

        DELAI_PREFERENTIEL = 14  # jours
        DELAI_MINIMUM = 7        # jours

        # trier les lignes CSV par date + horaire
        def parse_dt(row):
            try:
                return pd.to_datetime(f"{row['Date']} {row['Horaires']}", dayfirst=True)
            except:
                return pd.to_datetime("1900-01-01 00:00")

        df_sorted = df.copy()
        df_sorted['dt'] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        for _, row in df_sorted.iterrows():
            date = str(row["Date"]).strip() or "1900-01-01"
            horaire = str(row["Horaires"]).strip() or "00:00"
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]

            cle = f"{date} | {horaire}"
            repartition[cle] = []
            deja_affectes_par_date[cle] = set()

            date_horaire_dt = pd.to_datetime(f"{date} {horaire}", dayfirst=True, errors="coerce")
            if pd.isna(date_horaire_dt):
                date_horaire_dt = pd.to_datetime("1900-01-01 00:00")

            # ---- BINÔMES
            binomes_dispos = []
            for a, b in binomes:
                if (
                    a in dispos and b in dispos
                    and compteur[a] < max_occ_global
                    and compteur[b] < max_occ_global
                    and len(repartition[cle]) <= max_par_date - 2
                ):
                    # vérifier espacement
                    min_a = min([(date_horaire_dt - d).days for d in affectations[a]] + [float('inf')])
                    min_b = min([(date_horaire_dt - d).days for d in affectations[b]] + [float('inf')])
                    if min_a >= DELAI_MINIMUM and min_b >= DELAI_MINIMUM:
                        binomes_dispos.append((a, b))

            random.shuffle(binomes_dispos)
            for a, b in binomes_dispos:
                repartition[cle].extend([a, b])
                compteur[a] += 1
                compteur[b] += 1
                deja_affectes_par_date[cle].update([a, b])
                affectations[a].append(date_horaire_dt)
                affectations[b].append(date_horaire_dt)

            # ---- SOLO, triés par : plus grand espacement puis moins de créneaux
            score_solos = []
            for n in dispos:
                if n not in deja_affectes_par_date[cle] and compteur[n] < max_occ_global:
                    last_dates = affectations[n]
                    distance = min([(date_horaire_dt - d).days for d in last_dates] + [float('inf')])
                    score_solos.append((n, distance, compteur[n]))
            score_solos.sort(key=lambda x: (-x[1], x[2]))

            for nom, dist, _ in score_solos:
                if len(repartition[cle]) < max_par_date:
                    repartition[cle].append(nom)
                    compteur[nom] += 1
                    deja_affectes_par_date[cle].add(nom)
                    affectations[nom].append(date_horaire_dt)

            # ---- Compléter pour atteindre min_par_date si nécessaire
            restants = [n for n in noms_uniques if n not in deja_affectes_par_date[cle] and compteur[n] < max_occ_global]
            random.shuffle(restants)
            for n in restants:
                if len(repartition[cle]) < min_par_date:
                    repartition[cle].append(n)
                    compteur[n] += 1
                    deja_affectes_par_date[cle].add(n)
                    affectations[n].append(date_horaire_dt)
                else:
                    break

        # =====================================================
        # 7️⃣ TRI PAR DATE + HORAIRE (robuste)
        # =====================================================
        def cle_tri(cle):
            cle_str = str(cle)
            parts = cle_str.split("|", 1)
            date_str = parts[0].strip() if len(parts) > 0 else "1900-01-01"
            horaire_str = parts[1].strip() if len(parts) > 1 else "00:00"
            try:
                date_dt = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
                if pd.isna(date_dt):
                    date_dt = pd.to_datetime("1900-01-01")
            except:
                date_dt = pd.to_datetime("1900-01-01")
            try:
                heure_dt = pd.to_datetime(horaire_str, format="%H:%M", errors="coerce").time()
            except:
                heure_dt = pd.to_datetime("00:00", format="%H:%M").time()
            return (date_dt, heure_dt)

        repartition_tri = dict(sorted(repartition.items(), key=cle_tri))

        # =====================================================
        # 8️⃣ AFFICHAGE
        # =====================================================
        st.subheader("Répartition finale (triée par date et horaire)")
        for cle, enfants in repartition_tri.items():
            st.write(
                f"{cle} : "
                f"{', '.join(enfants) if enfants else 'Aucun'} "
                f"({max_par_date - len(enfants)} place(s) restante(s))"
            )

        st.subheader("Occurrences par enfant")
        st.write(dict(sorted(compteur.items())))

        jamais_affectes = [nom for nom, c in compteur.items() if c == 0]
        if jamais_affectes:
            st.subheader("Enfants jamais affectés")
            st.write(", ".join(jamais_affectes))

        # =====================================================
        # 9️⃣ EXPORT CSV
        # =====================================================
        export_df = pd.DataFrame([
            {
                "Date_Horaire": cle,
                "Enfants_affectés": ";".join(enfants),
                "Places_restantes": max_par_date - len(enfants)
            }
            for cle, enfants in repartition_tri.items()
        ])

        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger la répartition CSV",
            data=csv,
            file_name="repartition.csv",
            mime="text/csv"
        )
