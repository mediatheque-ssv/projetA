import streamlit as st
import pandas as pd
import random

st.title("Répartition mini-bénévoles")

st.markdown("""
<style>
/* Bouton principal */
.stButton>button {
    background-color: #6D28D9;
    color: white;
    border-radius: 12px;
    padding: 0.6em 1.2em;
    font-size: 1.05em;
    font-weight: 600;
}

/* Bouton au survol */
.stButton>button:hover {
    background-color: #5B21B6;
    color: white;
}

/* Séparateurs visuels */
hr {
    border: none;
    height: 2px;
    background-color: #DDD6FE;
    margin: 1.5em 0;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
st.markdown("## 📂 Import du CSV")
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
        
    st.markdown("### Aperçu du CSV")
    st.dataframe(df)

    # =====================================================
    # 2️⃣ EXTRACTION DES NOMS (avec binômes groupés)
    # =====================================================
    # Détection automatique du séparateur
    sample_cell = str(df["Noms_dispos"].iloc[0]) if len(df) > 0 else ""
    separator = "," if "," in sample_cell else ";"
    
    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        if pd.notna(cell)
        for n in str(cell).split(separator)
        if n.strip()
    })

    st.markdown("## 🧒 Enfants et binômes détectés")

    if noms_uniques:
        df_noms = pd.DataFrame(
            {
                "Enfant / binôme": noms_uniques,
                "Type": [
                    "Binôme" if "/" in nom else "Enfant seul"
                    for nom in noms_uniques
                ]
            }
        )

        st.dataframe(
            df_noms,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            f"🔎 {len(noms_uniques)} entité(s) détectée(s) • "
            f"Séparateur utilisé : '{separator}' • "
            "Les binômes doivent être notés sous la forme Nom1/Nom2"
        )
    else:
        st.warning("Aucun enfant détecté ! Vérifie le CSV")
        st.stop()


    # =====================================================
    # 3️⃣ PARAMÈTRES DES CRÉNEAUX
    # =====================================================
    st.markdown("## ⚙️ Paramètres des créneaux")
    col1, col2 = st.columns(2)

    with col1:
        min_par_date = st.slider(
            "👥 Minimum de personnes par créneau",
            min_value=1,
            max_value=10,
            value=4
        )

    with col2:
        max_par_date = st.slider(
            "👥 Maximum de personnes par créneau",
            min_value=min_par_date,
            max_value=10,
            value=max(5, min_par_date)
        )

    st.markdown("## 🎯 Limites d'occurrences par enfant/binôme")
    st.info("💡 Ces limites permettent d'éviter les répartitions extrêmes")

    col3, col4 = st.columns(2)

    with col3:
        min_occ_personne = st.slider("🔽 Minimum d'occurrences", 0, 10, 3)

    with col4:
        max_occ_personne = st.slider("🔼 Maximum d'occurrences", min_occ_personne, 20, 5)

    # =====================================================
    # 4️⃣ CALCUL DES DISPONIBILITÉS
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
    
    st.markdown("## 📊 Disponibilités par enfant / binôme")

    dispos_sorted = dict(sorted(dispos_par_entite.items(), key=lambda x: x[1]))

    df_dispos = (
        pd.DataFrame(
            dispos_sorted.items(),
            columns=["Enfant / binôme", "Nombre de disponibilités"]
        )
        .sort_values("Nombre de disponibilités")
        .reset_index(drop=True)
    )

    def style_dispos(val):
        if val <= 2:
            return "background-color: #FEE2E2"   # rouge doux
        elif val <= 4:
            return "background-color: #FEF9C3"   # jaune doux
        return ""

    st.dataframe(
        df_dispos.style.applymap(
            style_dispos,
            subset=["Nombre de disponibilités"]
        ),
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 5️⃣ RÉPARTITION AUTOMATIQUE
    # =====================================================
    st.markdown("---")
    st.markdown("## ▶️ 5. Lancer la répartition")
    if st.button("Répartir les enfants"):

        # Initialisation
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}
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

        # Algorithme en UN SEUL PASSAGE
        for creneau in creneaux_info:
            date_horaire_dt = creneau['dt']
            dispos = creneau['dispos']
            
            # Compter les personnes déjà affectées
            nb_personnes_affectees = sum(compter_personnes(n) for n in creneau['affectes'])
            
            # Créer liste de candidats
            candidats = []
            
            for n in dispos:
                if n not in creneau['affectes']:
                    distance = min([(date_horaire_dt - d).days for d in affectations[n]] + [float('inf')])
                    if distance >= DELAI_MINIMUM:
                        nb_dispos = dispos_par_entite[n]
                        # Bonus pour les très peu dispos
                        bonus = -100 if nb_dispos < 5 else 0
                        # Facteur aléatoire pour varier d'un trimestre à l'autre
                        alea_compteur = random.uniform(-0.5, 0.5)
                        alea_dispos = random.uniform(-1, 1)
                        candidats.append((n, compteur[n] + bonus + alea_compteur, nb_dispos + alea_dispos))
            
            # Trier : 1) compteur (avec bonus + aléa), 2) nb_dispos (avec aléa)
            candidats.sort(key=lambda x: (x[1], x[2]))
            
            # Affecter jusqu'au max de PERSONNES
            for nom, _, _ in candidats:
                nb_personnes_ce_nom = compter_personnes(nom)
                if nb_personnes_affectees + nb_personnes_ce_nom <= max_par_date:
                    creneau['affectes'].append(nom)
                    compteur[nom] += 1
                    affectations[nom].append(date_horaire_dt)
                    nb_personnes_affectees += nb_personnes_ce_nom

        # =====================================================
        # 6️⃣ TRI ET AFFICHAGE
        # =====================================================
        creneaux_info.sort(key=lambda x: x['dt'])

        st.markdown("## 🧩 Répartition finale")
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

        st.markdown("## 🔁 Occurrences par enfant / binôme")

        compteur_sorted = dict(sorted(compteur.items(), key=lambda x: x[1]))

        df_occ = (
            pd.DataFrame(
                compteur_sorted.items(),
                columns=["Enfant / binôme", "Nombre d'occurrences"]
            )
            .sort_values("Nombre d'occurrences")
            .reset_index(drop=True)
        )

        max_occ = df_occ["Nombre d'occurrences"].max()

        def style_occ(val):
            if val == 0:
                return "background-color: #FEE2E2"   # jamais affecté
            elif val == max_occ:
                return "background-color: #DDD6FE"   # violet clair (le plus sollicité)
            return ""

        st.dataframe(
            df_occ.style.applymap(
                style_occ,
                subset=["Nombre d'occurrences"]
            ),
            use_container_width=True,
            hide_index=True
        )


        jamais_affectes = [nom for nom, c in compteur.items() if c == 0]
        if jamais_affectes:
            st.markdown("## ⚠️ Enfants / binômes jamais affectés")
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
