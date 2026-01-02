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
    min_par_date = st.slider("Nombre minimal d'enfants par créneau", min_value=1, max_value=10, value=4)
    max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_value=min_par_date, max_value=10, value=max(5, min_par_date))

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

        repartition = {}
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}

        DELAI_MINIMUM = 7

        # Trier CSV par datetime (gérer mois en français)
        mois_fr = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }
        
        def parse_dt(row):
            try:
                date_str = str(row['Date']).strip().lower()
                horaire_str = str(row['Horaires']).strip()
                
                # Extraire jour et mois depuis "mercredi 7 janvier"
                parts = date_str.split()
                jour = int(parts[1]) if len(parts) > 1 else 1
                mois_nom = parts[2] if len(parts) > 2 else 'janvier'
                mois = mois_fr.get(mois_nom, 1)
                
                # Convertir "10h" en "10:00"
                horaire_str = horaire_str.replace('h', ':00') if 'h' in horaire_str else horaire_str
                heure = int(horaire_str.split(':')[0]) if ':' in horaire_str else 0
                minute = int(horaire_str.split(':')[1]) if ':' in horaire_str and len(horaire_str.split(':')) > 1 else 0
                
                return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure, minute=minute)
            except Exception as e:
                return pd.to_datetime("1900-01-01 00:00")
        
        df_sorted = df.copy()
        df_sorted['dt'] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        # Préparer la structure
        creneaux_info = []
        for _, row in df_sorted.iterrows():
            date = str(row["Date"]).strip() or "1900-01-01"
            horaire = str(row["Horaires"]).strip() or "00:00"
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(",") if n.strip()]
            cle = f"{date} | {horaire}"
            creneaux_info.append({
                'cle': cle,
                'dt': row['dt'],
                'dispos': dispos,
                'affectes': []
            })
            repartition[cle] = []

        # Algorithme par vagues
        vague = 0
        while True:
            vague += 1
            affectations_vague = 0
            
            # Mélanger l'ordre des créneaux pour cette vague
            creneaux_shuffled = creneaux_info.copy()
            random.shuffle(creneaux_shuffled)
            
            for creneau in creneaux_shuffled:
                if len(creneau['affectes']) >= max_par_date:
                    continue
                
                cle = creneau['cle']
                date_horaire_dt = creneau['dt']
                dispos = creneau['dispos']
                
                # ---- BINÔMES pour cette vague
                binomes_candidats = []
                for a, b in binomes:
                    if (
                        a in dispos and b in dispos
                        and a not in creneau['affectes']
                        and b not in creneau['affectes']
                        and compteur[a] < max_occ_global
                        and compteur[b] < max_occ_global
                    ):
                        # Vérifier espacement
                        min_a = min([(date_horaire_dt - d).days for d in affectations[a]] + [float('inf')])
                        min_b = min([(date_horaire_dt - d).days for d in affectations[b]] + [float('inf')])
                        if min_a >= DELAI_MINIMUM and min_b >= DELAI_MINIMUM:
                            binomes_candidats.append((a, b))
                
                random.shuffle(binomes_candidats)
                
                for a, b in binomes_candidats:
                    if len(creneau['affectes']) <= max_par_date - 2:
                        creneau['affectes'].extend([a, b])
                        compteur[a] += 1
                        compteur[b] += 1
                        affectations[a].append(date_horaire_dt)
                        affectations[b].append(date_horaire_dt)
                        affectations_vague += 2

                # ---- SOLO pour cette vague
                candidats_solo = []
                for n in dispos:
                    if (
                        n not in creneau['affectes']
                        and compteur[n] < max_occ_global
                    ):
                        last_dates = affectations[n]
                        distance = min([(date_horaire_dt - d).days for d in last_dates] + [float('inf')])
                        
                        if distance >= DELAI_MINIMUM:
                            candidats_solo.append(n)
                
                # Mélanger pour varier
                random.shuffle(candidats_solo)
                
                # Remplir jusqu'au max
                for nom in candidats_solo:
                    if len(creneau['affectes']) < max_par_date:
                        creneau['affectes'].append(nom)
                        compteur[nom] += 1
                        affectations[nom].append(date_horaire_dt)
                        affectations_vague += 1
            
            # Si aucune affectation dans cette vague, on arrête
            if affectations_vague == 0:
                break
            
            # Limite de sécurité
            if vague > 50:
                st.warning("Arrêt après 50 vagues (limite de sécurité)")
                break
        
        # Compléter les créneaux qui n'atteignent pas le minimum
        for creneau in creneaux_info:
            if len(creneau['affectes']) < min_par_date:
                cle = creneau['cle']
                date_horaire_dt = creneau['dt']
                dispos = creneau['dispos']
                
                # Prendre les moins affectés parmi les dispos
                candidats_补充 = [
                    (n, compteur[n]) for n in dispos
                    if n not in creneau['affectes'] and compteur[n] < max_occ_global
                ]
                candidats_补充.sort(key=lambda x: x[1])
                
                for nom, _ in candidats_补充:
                    if len(creneau['affectes']) < min_par_date:
                        creneau['affectes'].append(nom)
                        compteur[nom] += 1
                        affectations[nom].append(date_horaire_dt)
        
        # Copier les résultats dans repartition
        for creneau in creneaux_info:
            repartition[creneau['cle']] = creneau['affectes']

        # =====================================================
        # 7️⃣ TRI GARANTI PAR DATE/HORAIRE
        # =====================================================
        # On garde une map de la clé vers le datetime original
        cle_vers_dt = {}
        for _, row in df_sorted.iterrows():
            date = str(row["Date"]).strip() or "1900-01-01"
            horaire = str(row["Horaires"]).strip() or "00:00"
            cle = f"{date} | {horaire}"
            cle_vers_dt[cle] = row['dt']
        
        def cle_tri(item):
            cle = item[0]
            # Utiliser le datetime déjà parsé
            dt = cle_vers_dt.get(cle, pd.to_datetime("1900-01-01 00:00"))
            return dt

        repartition_tri_list = sorted(repartition.items(), key=cle_tri)

        # =====================================================
        # 8️⃣ AFFICHAGE
        # =====================================================
        st.subheader("Répartition finale (triée par date et horaire)")
        for cle, enfants in repartition_tri_list:
            st.write(
                f"{cle} : {', '.join(enfants) if enfants else 'Aucun'} "
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
        # 9️⃣ EXPORT CSV
        # =====================================================
        export_df = pd.DataFrame([
            {
                "Date_Horaire": cle,
                "Enfants_affectés": ";".join(enfants),
                "Places_restantes": max_par_date - len(enfants)
            }
            for cle, enfants in repartition_tri_list
        ])

        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger la répartition CSV",
            data=csv,
            file_name="repartition.csv",
            mime="text/csv"
        )
