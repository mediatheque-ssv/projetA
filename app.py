import streamlit as st
import pandas as pd
import random
from collections import defaultdict, Counter

st.title("Répartition optimale / équilibrée (version ultime)")

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

    if not set(["Date", "Horaires", "Noms_dispos"]).issubset(set(df.columns)):
        st.error(f"Colonnes attendues : Date, Horaires, Noms_dispos\nColonnes trouvées : {df.columns.tolist()}")
        st.stop()

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
    st.write(noms_uniques)
    st.info(f"Séparateur détecté : '{separator}'")

    # =====================================================
    # 3️⃣ PARAMÈTRES
    # =====================================================
    st.subheader("Paramètres des créneaux")
    min_par_date = st.slider("Nombre minimal d'enfants par créneau", 1, 10, 4)
    max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_par_date, 10, max(min_par_date, 5))
    DELAI_MINIMUM = 7

    # =====================================================
    # 4️⃣ BINÔMES
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
    # 5️⃣ RÉPARTITION
    # =====================================================
    if st.button("Répartir les enfants"):

        # Parser les dates
        mois_fr = {'janvier':1,'février':2,'mars':3,'avril':4,'mai':5,'juin':6,
                   'juillet':7,'août':8,'septembre':9,'octobre':10,'novembre':11,'décembre':12}

        def parse_dt(row):
            try:
                date_str = str(row['Date']).strip().lower()
                horaire_str = str(row['Horaires']).strip()
                parts = date_str.split()
                jour = int(parts[1]) if len(parts)>1 else 1
                mois = mois_fr.get(parts[2],1) if len(parts)>2 else 1
                if 'h' in horaire_str: horaire_str = horaire_str.replace('h', ':00')
                heure = int(horaire_str.split(':')[0]) if ':' in horaire_str else 0
                minute = int(horaire_str.split(':')[1]) if ':' in horaire_str and len(horaire_str.split(':'))>1 else 0
                return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure, minute=minute)
            except:
                return pd.to_datetime("1900-01-01 00:00")

        df_sorted = df.copy()
        df_sorted['dt'] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        # Préparer créneaux
        creneaux_info = []
        for _, row in df_sorted.iterrows():
            date = str(row["Date"]).strip()
            horaire = str(row["Horaires"]).strip()
            dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
            dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip() and n in noms_uniques]
            cle = f"{date} | {horaire}"
            creneaux_info.append({'cle': cle, 'dt': row['dt'], 'dispos': dispos, 'affectes': []})

        total_places = len(creneaux_info)*max_par_date

        # Calcul occurrences idéales
        occ_ideale = total_places // len(noms_uniques)
        compteur = Counter()
        affectations = defaultdict(list)

        # Construire liste globale à placer
        liste_a_placer = []
        for n in noms_uniques:
            for _ in range(occ_ideale):
                liste_a_placer.append(n)
        random.shuffle(liste_a_placer)

        # Boucle round robin sur les créneaux
        for creneau in creneaux_info:

            # 1️⃣ Affecter binômes en priorité
            for a,b in binomes:
                if a in creneau['dispos'] and b in creneau['dispos'] \
                   and a not in creneau['affectes'] and b not in creneau['affectes'] \
                   and compteur[a]<occ_ideale and compteur[b]<occ_ideale \
                   and len(creneau['affectes'])<=max_par_date-2:
                    # DELAI_MINIMUM respecté si possible
                    min_a = min([(creneau['dt']-d).days for d in affectations[a]]+[float('inf')])
                    min_b = min([(creneau['dt']-d).days for d in affectations[b]]+[float('inf')])
                    if min_a>=DELAI_MINIMUM and min_b>=DELAI_MINIMUM or len(creneau['affectes'])<min_par_date:
                        creneau['affectes'].extend([a,b])
                        compteur[a]+=1; compteur[b]+=1
                        affectations[a].append(creneau['dt'])
                        affectations[b].append(creneau['dt'])

            # 2️⃣ Affecter solos
            candidats = [n for n in creneau['dispos'] if n not in creneau['affectes'] and compteur[n]<occ_ideale]
            candidats.sort(key=lambda n: compteur[n])
            for n in candidats:
                if len(creneau['affectes'])<max_par_date:
                    min_dist = min([(creneau['dt']-d).days for d in affectations[n]]+[float('inf')])
                    if min_dist>=DELAI_MINIMUM or len(creneau['affectes'])<min_par_date:
                        creneau['affectes'].append(n)
                        compteur[n]+=1
                        affectations[n].append(creneau['dt'])

        # =====================================================
        # TRI ET AFFICHAGE
        # =====================================================
        creneaux_info.sort(key=lambda x:x['dt'])
        st.subheader("Répartition finale")
        for c in creneaux_info:
            st.write(f"{c['cle']} : {', '.join(c['affectes']) if c['affectes'] else 'Aucun'} "
                     f"({max_par_date-len(c['affectes'])} place(s) restante(s))")

        st.subheader("Occurrences par enfant")
        st.write(dict(sorted(compteur.items(), key=lambda x:x[1])))

        jamais_affectes = [n for n,c in compteur.items() if c==0]
        if jamais_affectes:
            st.subheader("Enfants jamais affectés")
            st.write(", ".join(jamais_affectes))

        # =====================================================
        # EXPORT CSV
        # =====================================================
        export_df = pd.DataFrame([
            {"Date_Horaire": c['cle'],
             "Enfants_affectés": separator.join(c['affectes']),
             "Places_restantes": max_par_date-len(c['affectes'])}
            for c in creneaux_info
        ])
        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger la répartition CSV",
            data=csv,
            file_name="repartition.csv",
            mime="text/csv"
        )
