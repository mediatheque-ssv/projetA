import streamlit as st
import pandas as pd
from collections import defaultdict

st.title("Répartition égalitaire bénévoles / enfants (étalée)")

@@ -13,7 +14,6 @@

if uploaded_file:

    # Lecture CSV
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    except Exception as e:
@@ -33,12 +33,11 @@
    st.dataframe(df)

    # =====================================================
    # 2️⃣ EXTRACTION DES NOMS (avec binômes groupés)
    # 2️⃣ EXTRACTION DES NOMS
    # =====================================================
    # Détection automatique du séparateur
    sample_cell = str(df["Noms_dispos"].iloc[0]) if len(df) > 0 else ""
    separator = "," if "," in sample_cell else ";"
    

    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
@@ -48,179 +47,118 @@
    })

    st.subheader("Enfants/Binômes détectés")
    if noms_uniques:
        st.write(noms_uniques)
        st.info(f"Séparateur détecté : '{separator}'. Les binômes doivent être notés 'Nom1/Nom2' dans le CSV.")
    else:
        st.warning("Aucun enfant détecté ! Vérifie le CSV")
        st.stop()
    st.write(noms_uniques)

    # =====================================================
    # 3️⃣ PARAMÈTRES DES CRÉNEAUX
    # 3️⃣ PARAMÈTRES
    # =====================================================
    st.subheader("Paramètres des créneaux")
    min_par_date = st.slider("Nombre minimal de PERSONNES par créneau", min_value=1, max_value=10, value=4)
    max_par_date = st.slider("Nombre maximal de PERSONNES par créneau", min_value=min_par_date, max_value=10, value=max(5, min_par_date))
    min_par_date = st.slider("Nombre minimal de PERSONNES par créneau", 1, 10, 4)
    max_par_date = st.slider("Nombre maximal de PERSONNES par créneau", min_par_date, 10, max(5, min_par_date))

    # =====================================================
    # 4️⃣ CALCUL DES DISPONIBILITÉS
    # 4️⃣ DISPONIBILITÉS
    # =====================================================
    total_creaneaux = len(df)
    
    # Compter les personnes réelles (binômes = 2 personnes)
    def compter_personnes(nom):
        return len(nom.split("/"))
    
    # Calculer les dispos de chaque entité

    dispos_par_entite = {nom: 0 for nom in noms_uniques}
    for _, row in df.iterrows():
        dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
        dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
        for n in dispos:
            if n in dispos_par_entite:
                dispos_par_entite[n] += 1
    
        if pd.notna(row["Noms_dispos"]):
            for n in str(row["Noms_dispos"]).split(separator):
                n = n.strip()
                if n in dispos_par_entite:
                    dispos_par_entite[n] += 1

    st.subheader("Disponibilités par enfant/binôme")
    dispos_sorted = dict(sorted(dispos_par_entite.items(), key=lambda x: x[1]))
    st.write(dispos_sorted)
    st.write(dict(sorted(dispos_par_entite.items(), key=lambda x: x[1])))

    # =====================================================
    # 5️⃣ RÉPARTITION AUTOMATIQUE
    # 5️⃣ RÉPARTITION
    # =====================================================
    if st.button("Répartir les enfants"):

        # Initialisation
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}
        ensemble = defaultdict(int)   # 👈 mémoire déjà ensemble
        DELAI_MINIMUM = 6

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
                parts = str(row['Date']).lower().split()
                jour = int(parts[1])
                mois = mois_fr.get(parts[2], 1)
                heure = int(str(row['Horaires']).split('h')[0])
                return pd.Timestamp(2026, mois, jour, heure)
            except:
                return pd.to_datetime("1900-01-01 00:00")
        
                return pd.Timestamp("1900-01-01")

        df_sorted = df.copy()
        df_sorted['dt'] = df_sorted.apply(parse_dt, axis=1)
        df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
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
            dispos = []
            if pd.notna(row["Noms_dispos"]):
                dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator)]
            creneaux_info.append({
                'cle': cle,
                'dt': row['dt'],
                'dispos': dispos,
                'affectes': []
                "cle": f"{row['Date']} | {row['Horaires']}",
                "dt": row["dt"],
                "dispos": dispos,
                "affectes": []
            })

        # Algorithme en UN SEUL PASSAGE
        for creneau in creneaux_info:
            date_horaire_dt = creneau['dt']
            dispos = creneau['dispos']
            
            # Compter les personnes déjà affectées
            nb_personnes_affectees = sum(compter_personnes(n) for n in creneau['affectes'])
            
            # Créer liste de candidats
            nb_personnes = 0
            candidats = []
            
            for n in dispos:
                if n not in creneau['affectes']:
                    distance = min([(date_horaire_dt - d).days for d in affectations[n]] + [float('inf')])

            for n in creneau["dispos"]:
                if n in compteur:
                    distance = min([(creneau["dt"] - d).days for d in affectations[n]] + [999])
                    if distance >= DELAI_MINIMUM:
                        nb_dispos = dispos_par_entite[n]
                        # Bonus pour les très peu dispos
                        bonus = -min(nb_dispos, 10)
                        candidats.append((n, compteur[n] + bonus, nb_dispos))
            
            # Trier : 1) compteur (avec bonus), 2) nb_dispos
                        bonus = -100 if dispos_par_entite[n] < 5 else 0

                        # 🔸 pénalité déjà ensemble
                        penalite = 0
                        for a in creneau["affectes"]:
                            paire = tuple(sorted([n, a]))
                            penalite += ensemble[paire]

                        score = compteur[n] + bonus + penalite * 2
                        candidats.append((n, score, dispos_par_entite[n]))

            candidats.sort(key=lambda x: (x[1], x[2]))
            
            # Affecter jusqu'au max de PERSONNES

            for nom, _, _ in candidats:
                nb_personnes_ce_nom = compter_personnes(nom)
                if nb_personnes_affectees + nb_personnes_ce_nom <= max_par_date:
                    creneau['affectes'].append(nom)
                p = compter_personnes(nom)
                if nb_personnes + p <= max_par_date:
                    creneau["affectes"].append(nom)

                    # 🔸 mise à jour mémoire ensemble
                    for autre in creneau["affectes"]:
                        if autre != nom:
                            paire = tuple(sorted([nom, autre]))
                            ensemble[paire] += 1

                    compteur[nom] += 1
                    affectations[nom].append(date_horaire_dt)
                    nb_personnes_affectees += nb_personnes_ce_nom
                    affectations[nom].append(creneau["dt"])
                    nb_personnes += p

        # =====================================================
        # 6️⃣ TRI ET AFFICHAGE
        # 6️⃣ AFFICHAGE
        # =====================================================
        creneaux_info.sort(key=lambda x: x['dt'])

        st.subheader("Répartition finale (triée par date et horaire)")
        for creneau in creneaux_info:
            enfants_raw = creneau['affectes']
            # Décomposer les binômes pour l'affichage
            enfants_affichage = []
            for e in enfants_raw:
                if "/" in e:
                    enfants_affichage.extend(e.split("/"))
                else:
                    enfants_affichage.append(e)
            
            nb_personnes = len(enfants_affichage)
            st.write(
                f"{creneau['cle']} : {', '.join(enfants_affichage) if enfants_affichage else 'Aucun'} "
                f"({max_par_date - nb_personnes} place(s) restante(s))"
            )
        st.subheader("Répartition finale")
        for c in creneaux_info:
            affichage = []
            for n in c["affectes"]:
                affichage.extend(n.split("/"))
            st.write(f"{c['cle']} : {', '.join(affichage)}")

        st.subheader("Occurrences par enfant/binôme")
        compteur_sorted = dict(sorted(compteur.items(), key=lambda x: x[1]))
        st.write(compteur_sorted)

        jamais_affectes = [nom for nom, c in compteur.items() if c == 0]
        if jamais_affectes:
            st.subheader("Enfants/binômes jamais affectés")
            st.write(", ".join(jamais_affectes))

        # =====================================================
        # 7️⃣ EXPORT CSV
        # =====================================================
        export_df = pd.DataFrame([
            {
                "Date_Horaire": creneau['cle'],
                "Enfants_affectés": separator.join([
                    e.replace("/", " et ") for e in creneau['affectes']
                ]),
                "Places_restantes": max_par_date - sum(compter_personnes(n) for n in creneau['affectes'])
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
        st.write(dict(sorted(compteur.items(), key=lambda x: x[1])))
