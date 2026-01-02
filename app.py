import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

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
    # Détection automatique du séparateur (virgule ou point-virgule)
    sample_cell = str(df["Noms_dispos"].iloc[0]) if len(df) > 0 else ""
    separator = "," if "," in sample_cell else ";"

    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        if pd.notna(cell)
        for n in str(cell).split(separator)
        if n.strip()
    })

    st.subheader("Enfants détectés")
    if noms_uniques:
        st.write(noms_uniques)
        st.info(f"Séparateur détecté : '{separator}'")
    else:
        st.warning("Aucun enfant détecté ! Vérifie le CSV")
        st.stop()

    # =====================================================
    # 3️⃣ PARAMÈTRES DES CRÉNEAUX
    # =====================================================
    st.subheader("Paramètres des créneaux")
    min_par_date = st.slider("Nombre minimal d'enfants par créneau", min_value=1, max_value=10, value=4)
    max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_value=min_par_date, max_value=10, value=max(5, min_par_date))
    delai_minimum = st.slider("Délai minimum entre deux créneaux pour un même enfant (jours)", min_value=1, max_value=14, value=7)

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
        st.write("Binômes définis :")
        for a, b in st.session_state.binomes:
            st.write(f"- {a} + {b}")

    binomes = st.session_state.binomes

    # =====================================================
    # 6️⃣ RÉPARTITION PAR VAGUES SUCCESSIVES
    # =====================================================
    if st.button("Répartir les enfants"):

        # Initialisation
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}
        binomes_non_places = []

        # Parsing des dates (version simplifiée)
        mois_fr = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }

        def parse_dt(row):
            try:
                date_str = str(row['Date']).strip().lower()
                horaire_str = str(row['Horaires']).strip()
                parts = date_str.split()
                jour = int(parts[1])
                mois = mois_fr[parts[2]]
                annee = 2026  # ou l'année de ton choix
                heure = int(horaire_str.split(':')[0]) if ':' in horaire_str else 0
                return pd.Timestamp(year=annee, month=mois, day=jour, hour=heure)
            except:
                return pd.to_datetime("1900-01-01 00:00")

        df_sorted = df.copy()
        df_sorted['dt'] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        # Préparer les créneaux
        creneaux_info = []
        for _, row in df_sorted.iterrows():
            date = str(row["Date"]).strip() or "1900-01-01"
            horaire = str(row["Horaires"]).strip() or "00:00"
            dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
            dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
            dispos = [n for n in dispos if n in compteur]

            cle = f"{date} | {horaire}"
            creneaux_info.append({
                'cle': cle,
                'dt': row['dt'],
                'dispos': dispos,
                'affectes': []
            })

        # Algorithme par vagues
        vague = 0
        places_restantes_total = sum(max_par_date for _ in creneaux_info)

        while vague < 50:
            vague += 1
            affectations_vague = 0
            creneaux_shuffled = creneaux_info.copy()
            random.shuffle(creneaux_shuffled)

            for creneau in creneaux_shuffled:
                if len(creneau['affectes']) >= max_par_date:
                    continue

                cle = creneau['cle']
                date_horaire_dt = creneau['dt']
                dispos = creneau['dispos']

                # BINÔMES
                for a, b in binomes:
                    if (
                        a in dispos and b in dispos
                        and a not in creneau['affectes']
                        and b not in creneau['affectes']
                        and compteur[a] < max_occ_global
                        and compteur[b] < max_occ_global
                        and len(creneau['affectes']) <= max_par_date - 2
                    ):
                        min_a = min([(date_horaire_dt - d).days for d in affectations[a]] + [float('inf')])
                        min_b = min([(date_horaire_dt - d).days for d in affectations[b]] + [float('inf')])
                        if min_a >= delai_minimum and min_b >= delai_minimum:
                            creneau['affectes'].extend([a, b])
                            compteur[a] += 1
                            compteur[b] += 1
                            affectations[a].append(date_horaire_dt)
                            affectations[b].append(date_horaire_dt)
                            affectations_vague += 2
                        else:
                            if (a, b) not in binomes_non_places:
                                binomes_non_places.append((a, b))

                # SOLO
                candidats_solo = []
                for n in dispos:
                    if (
                        n not in creneau['affectes']
                        and compteur[n] < max_occ_global
                    ):
                        distance = min([(date_horaire_dt - d).days for d in affectations[n]] + [float('inf')])
                        if distance >= delai_minimum:
                            candidats_solo.append(n)

                random.shuffle(candidats_solo)

                for nom in candidats_solo:
                    if len(creneau['affectes']) < max_par_date:
                        creneau['affectes'].append(nom)
                        compteur[nom] += 1
                        affectations[nom].append(date_horaire_dt)
                        affectations_vague += 1

            if affectations_vague == 0:
                break

        # Compléter les créneaux sous le minimum
        for creneau in creneaux_info:
            if len(creneau['affectes']) < min_par_date:
                candidats = [(n, compteur[n]) for n in creneau['dispos']
                           if n not in creneau['affectes'] and compteur[n] < max_occ_global]
                candidats.sort(key=lambda x: x[1])

                for nom, _ in candidats:
                    if len(creneau['affectes']) < min_par_date:
                        creneau['affectes'].append(nom)
                        compteur[nom] += 1
                        affectations[nom].append(creneau['dt'])

        # =====================================================
        # 7️⃣ TRI ET AFFICHAGE
        # =====================================================
        creneaux_info.sort(key=lambda x: x['dt'])

        st.subheader("Répartition finale (triée par date et horaire)")
        for creneau in creneaux_info:
            enfants = creneau['affectes']
            st.write(
                f"{creneau['cle']} : {', '.join(enfants) if enfants else 'Aucun'} "
                f"({max_par_date - len(enfants)} place(s) restante(s))"
            )

        # =====================================================
        # 8️⃣ VISUALISATION
        # =====================================================
        st.subheader("Occurrences par enfant")
        fig, ax = plt.subplots()
        ax.bar(compteur.keys(), compteur.values())
        ax.set_xticklabels(compteur.keys(), rotation=90)
        ax.set_ylabel("Nombre d'occurrences")
        st.pyplot(fig)

        # =====================================================
        # 9️⃣ ALERTES
        # =====================================================
        jamais_affectes = [nom for nom, c in compteur.items() if c == 0]
        if jamais_affectes:
            st.warning("Enfants jamais affectés : " + ", ".join(jamais_affectes))

        if binomes_non_places:
            st.warning("Binômes non placés (délai ou max_occ_global) : " + ", ".join([f"{a}+{b}" for a, b in binomes_non_places]))

        # =====================================================
        # 10️⃣ EXPORT CSV
        # =====================================================
        export_df = pd.DataFrame([
            {
                "Date_Horaire": creneau['cle'],
                "Enfants_affectés": separator.join(creneau['affectes']),
                "Places_restantes": max_par_date - len(creneau['affectes'])
            }
            for creneau in creneaux_info
        ])

        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger la répartition CSV",
            data=csv,
            file_name="repartition.csv",
            mime="text/csv"
        )
