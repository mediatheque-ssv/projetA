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

    # =====================================================
    # 4️⃣ CALCUL DES DISPONIBILITÉS
    # =====================================================
    total_creaneaux = len(df)
    
    # Calculer les dispos de chaque enfant
    dispos_par_enfant = {nom: 0 for nom in noms_uniques}
    for _, row in df.iterrows():
        dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
        dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
        for n in dispos:
            if n in dispos_par_enfant:
                dispos_par_enfant[n] += 1
    
    st.subheader("Disponibilités par enfant")
    dispos_sorted = dict(sorted(dispos_par_enfant.items(), key=lambda x: x[1]))
    st.write(dispos_sorted)
    
    st.info("L'algorithme priorise automatiquement les personnes les moins disponibles")

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

        # Initialisation (pas de limite max par enfant)
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}
        DELAI_MINIMUM = 6  # 6 jours pour éviter mercredi→samedi mais permettre mercredi→mercredi

        # Parser les dates en français
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
            date = str(row["Date"]).strip() or "1900-01-01"
            horaire = str(row["Horaires"]).strip() or "00:00"
            dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
            dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
            # Filtrer pour garder seulement les noms reconnus
            dispos = [n for n in dispos if n in compteur]
            
            cle = f"{date} | {horaire}"
            creneaux_info.append({
                'cle': cle,
                'dt': row['dt'],
                'dispos': dispos,
                'affectes': []
            })

        # Algorithme par vagues avec priorité égalité stricte
        vague = 0
        
        while vague < 50:
            vague += 1
            affectations_vague = 0
            
            # Traiter les créneaux dans l'ordre chrono (pas de shuffle)
            for creneau in creneaux_info:
                if len(creneau['affectes']) >= max_par_date:
                    continue
                
                date_horaire_dt = creneau['dt']
                dispos = creneau['dispos']
                
                # BINÔMES en priorité (pas de limite max)
                binomes_ok = []
                for a, b in binomes:
                    if (
                        a in dispos and b in dispos
                        and a not in creneau['affectes']
                        and b not in creneau['affectes']
                        and len(creneau['affectes']) <= max_par_date - 2
                    ):
                        min_a = min([(date_horaire_dt - d).days for d in affectations[a]] + [float('inf')])
                        min_b = min([(date_horaire_dt - d).days for d in affectations[b]] + [float('inf')])
                        if min_a >= DELAI_MINIMUM and min_b >= DELAI_MINIMUM:
                            total_dispos = dispos_par_enfant[a] + dispos_par_enfant[b]
                            binomes_ok.append((a, b, total_dispos))
                
                # Prendre le binôme le moins dispo globalement
                binomes_ok.sort(key=lambda x: (dispos_par_enfant[x[0]] + dispos_par_enfant[x[1]]))
                if binomes_ok:
                    a, b, _ = binomes_ok[0]
                    creneau['affectes'].extend([a, b])
                    compteur[a] += 1
                    compteur[b] += 1
                    affectations[a].append(date_horaire_dt)
                    affectations[b].append(date_horaire_dt)
                    affectations_vague += 2

                # SOLO : trier d'abord par compteur, puis par nb_dispos
                candidats_solo = []
                for n in dispos:
                    if n not in creneau['affectes']:
                        distance = min([(date_horaire_dt - d).days for d in affectations[n]] + [float('inf')])
                        if distance >= DELAI_MINIMUM:
                            nb_dispos = dispos_par_enfant[n]
                            candidats_solo.append((n, compteur[n], nb_dispos))
                
                # Trier par : 1) compteur (priorité aux moins affectés), 2) nb_dispos (moins dispos en cas d'égalité)
                candidats_solo.sort(key=lambda x: (x[1], x[2]))
                
                # Prendre seulement jusqu'au max (laisser des places vides si besoin)
                places_dispo = max_par_date - len(creneau['affectes'])
                for nom, _, _ in candidats_solo[:places_dispo]:
                    creneau['affectes'].append(nom)
                    compteur[nom] += 1
                    affectations[nom].append(date_horaire_dt)
                    affectations_vague += 1
            
            if affectations_vague == 0:
                break
        
        # NE PAS compléter automatiquement le min - laisser des places vides si nécessaire

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

        st.subheader("Occurrences par enfant")
        compteur_sorted = dict(sorted(compteur.items(), key=lambda x: x[1]))
        st.write(compteur_sorted)

        jamais_affectes = [nom for nom, c in compteur.items() if c == 0]
        if jamais_affectes:
            st.subheader("Enfants jamais affectés")
            st.write(", ".join(jamais_affectes))

        # =====================================================
        # 8️⃣ EXPORT CSV
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
