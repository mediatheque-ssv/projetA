import streamlit as st
import pandas as pd
import random
from collections import defaultdict

st.title("Répartition optimale bénévoles / enfants (solveur global)")

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
    DELAI_MINIMUM = 7

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
    # 6️⃣ RÉPARTITION OPTIMALE
    # =====================================================
    if st.button("Répartir les enfants"):

        # Parser les dates
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
                jour = int(parts[1]) if len(parts) > 1 else 1
                mois_nom = parts[2] if len(parts) > 2 else 'janvier'
                mois = mois_fr.get(mois_nom, 1)
                
                horaire_str = horaire_str.replace('h', ':00') if 'h' in horaire_str else horaire_str
                heure = int(horaire_str.split(':')[0]) if ':' in horaire_str else 0
                minute = int(horaire_str.split(':')[1]) if ':' in horaire_str and len(horaire_str.split(':')) > 1 else 0
                
                return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure, minute=minute)
            except:
                return pd.to_datetime("1900-01-01 00:00")

        df_sorted = df.copy()
        df_sorted['dt'] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        # Préparer les créneaux
        creneaux_info = []
        for _, row in df_sorted.iterrows():
            date = str(row["Date"]).strip()
            horaire = str(row["Horaires"]).strip()
            dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
            dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
            dispos = [n for n in dispos if n in noms_uniques]
            cle = f"{date} | {horaire}"
            creneaux_info.append({'cle': cle, 'dt': row['dt'], 'dispos': dispos, 'affectes': []})

        # Calculer occurrences idéales par enfant
        occ_ideale = {n: 0 for n in noms_uniques}
        total_places = len(creneaux_info) * max_par_date
        for n in noms_uniques:
            occ_ideale[n] = min(max_occ_global, round(total_places / len(noms_uniques)))

        # Dictionnaire pour suivre dates affectées
        affectations = defaultdict(list)
        compteur = {n: 0 for n in noms_uniques}

        # Boucle sur les créneaux pour affecter les enfants
        for creneau in creneaux_info:

            # 1️⃣ Affecter les binômes si possible
            for a, b in binomes:
                if (
                    a in creneau['dispos'] and b in creneau['dispos']
                    and a not in creneau['affectes'] and b not in creneau['affectes']
                    and compteur[a] < occ_ideale[a] and compteur[b] < occ_ideale[b]
                    and len(creneau['affectes']) <= max_par_date - 2
                ):
                    # Respect DELAI_MINIMUM si possible
                    min_a = min([(creneau['dt'] - d).days for d in affectations[a]] + [float('inf')])
                    min_b = min([(creneau['dt'] - d).days for d in affectations[b]] + [float('inf')])
                    if min_a >= DELAI_MINIMUM and min_b >= DELAI_MINIMUM:
                        creneau['affectes'].extend([a, b])
                        compteur[a] += 1
                        compteur[b] += 1
                        affectations[a].append(creneau['dt'])
                        affectations[b].append(creneau['dt'])

            # 2️⃣ Affecter les solos, triés par nombre d'affectations restantes
            candidats = [
                n for n in creneau['dispos']
                if n not in creneau['affectes'] and compteur[n] < occ_ideale[n]
            ]
            candidats.sort(key=lambda n: compteur[n])  # priorité à ceux qui ont moins de créneaux

            for n in candidats:
                if len(creneau['affectes']) < max_par_date:
                    min_distance = min([(creneau['dt'] - d).days for d in affectations[n]] + [float('inf')])
                    if min_distance >= DELAI_MINIMUM or len(creneau['affectes']) < min_par_date:
                        creneau['affectes'].append(n)
                        compteur[n] += 1
                        affectations[n].append(creneau['dt'])

        # =====================================================
        # TRI ET AFFICHAGE
        # =====================================================
        creneaux_info.sort(key=lambda x: x['dt'])

        st.subheader("Répartition finale (triée par date et horaire)")
        for creneau in creneaux_info:
            enfants = creneau['affectes']
            st.write(f"{creneau['cle']} : {', '.join(enfants) if enfants else 'Aucun'} "
                     f"({max_par_date - len(enfants)} place(s) restante(s))")

        st.subheader("Occurrences par enfant")
        st.write(dict(sorted(compteur.items(), key=lambda x: x[1])))

        jamais_affectes = [n for n, c in compteur.items() if c == 0]
        if jamais_affectes:
            st.subheader("Enfants jamais affectés")
            st.write(", ".join(jamais_affectes))

        # =====================================================
        # EXPORT CSV
        # =====================================================
        export_df = pd.DataFrame([
            {"Date_Horaire": c['cle'],
             "Enfants_affectés": separator.join(c['affectes']),
             "Places_restantes": max_par_date - len(c['affectes'])}
            for c in creneaux_info
        ])
        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger la répartition CSV",
            data=csv,
            file_name="repartition.csv",
            mime="text/csv"
        )
