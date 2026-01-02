import streamlit as st
import pandas as pd
import random

st.title("Répartition équilibrée des enfants / binômes")

# =====================================================
# 1️⃣ Import CSV
# =====================================================
uploaded_file = st.file_uploader("Importer le CSV (Date ; Horaires ; Noms_dispos)", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    except Exception as e:
        st.error(f"Erreur de lecture du CSV : {e}")
        st.stop()

    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    if not set(["Date", "Horaires", "Noms_dispos"]).issubset(set(df.columns)):
        st.error(f"Colonnes manquantes. Attendu : Date, Horaires, Noms_dispos. Trouvé : {df.columns.tolist()}")
        st.stop()

    st.subheader("Aperçu du CSV")
    st.dataframe(df.head(10))

    # =====================================================
    # 2️⃣ Extraction des noms
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

    # =====================================================
    # 3️⃣ Paramètres
    # =====================================================
    st.subheader("Paramètres généraux")
    min_par_date = st.slider("Nombre minimal d'enfants par créneau", 1, 10, 2)
    max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_par_date, 10, 5)
    delai_minimum = st.slider("Délai minimum entre deux présences (jours)", 1, 14, 7)

    # =====================================================
    # 4️⃣ Occurrence minimale par enfant
    # =====================================================
    st.subheader("Occurrence minimale par enfant")
    disponibilites_totales = {nom: sum(nom in str(cell).split(separator) for cell in df["Noms_dispos"]) for nom in noms_uniques}
    occur_min = {}
    col1, col2 = st.columns(2)
    for i, nom in enumerate(noms_uniques):
        with col1 if i % 2 == 0 else col2:
            occur_min[nom] = st.number_input(
                f"{nom} (max dispo {disponibilites_totales[nom]})",
                min_value=0,
                max_value=disponibilites_totales[nom],
                value=min(2, disponibilites_totales[nom])
            )

    # =====================================================
    # 5️⃣ Gestion des binômes
    # =====================================================
    st.subheader("Binômes à ne pas séparer")
    if "binomes" not in st.session_state:
        st.session_state.binomes = []

    col1, col2 = st.columns(2)
    with col1:
        enfant_a = st.selectbox("Enfant A", noms_uniques, key="a")
    with col2:
        enfant_b = st.selectbox("Enfant B", noms_uniques, key="b")

    if (enfant_a != enfant_b and
        st.button("Ajouter le binôme") and
        (enfant_a, enfant_b) not in st.session_state.binomes and
        (enfant_b, enfant_a) not in st.session_state.binomes):
        st.session_state.binomes.append((enfant_a, enfant_b))

    if st.session_state.binomes:
        st.write("Binômes définis :")
        for a, b in st.session_state.binomes:
            st.write(f"- {a} + {b}")

    # =====================================================
    # 6️⃣ Parsing dates
    # =====================================================
    mois_fr = {'janvier':1, 'février':2, 'fevrier':2, 'mars':3}

    def parse_dt(row):
        try:
            date_str = str(row['Date']).strip().lower()
            horaire_str = str(row['Horaires']).strip()
            parts = date_str.split()
            if len(parts) < 3:
                return pd.Timestamp("1900-01-01")
            jour = int(parts[1])
            mois = mois_fr.get(parts[2], 1)
            annee = 2026
            heure = int(horaire_str.split('h')[0]) if 'h' in horaire_str else 0
            return pd.Timestamp(year=annee, month=mois, day=jour, hour=heure)
        except:
            return pd.Timestamp("1900-01-01")

    df['dt'] = df.apply(parse_dt, axis=1)
    df_sorted = df.sort_values("dt")
    creneaux_info = []
    for _, row in df_sorted.iterrows():
        if row['dt'] == pd.Timestamp("1900-01-01"):
            continue
        dispo = [n.strip() for n in str(row["Noms_dispos"]).split(separator) if n.strip() in noms_uniques]
        creneaux_info.append({
            'cle': f"{row['Date']} | {row['Horaires']}",
            'dt': row['dt'],
            'dispos': dispo,
            'affectes': []
        })

    # =====================================================
    # 7️⃣ Répartition
    # =====================================================
    if st.button("Lancer la répartition"):
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}

        # Étape 1 : remplir chaque enfant jusqu'à occurrence_min
        for nom in noms_uniques:
            places_restantes = occur_min[nom]
            for creneau in creneaux_info:
                if places_restantes <= 0:
                    break
                if nom not in creneau['dispos'] or nom in creneau['affectes']:
                    continue
                last = affectations[nom][-1] if affectations[nom] else pd.Timestamp("1900-01-01")
                if (creneau['dt'] - last).days < delai_minimum:
                    continue
                if len(creneau['affectes']) >= max_par_date:
                    continue
                # Affecter l'enfant
                creneau['affectes'].append(nom)
                compteur[nom] += 1
                affectations[nom].append(creneau['dt'])
                places_restantes -= 1
                # Affecter le binôme si nécessaire
                for a,b in st.session_state.binomes:
                    if a==nom and b in creneau['dispos'] and b not in creneau['affectes']:
                        if len(creneau['affectes']) < max_par_date:
                            creneau['affectes'].append(b)
                            compteur[b] += 1
                            affectations[b].append(creneau['dt'])
                    if b==nom and a in creneau['dispos'] and a not in creneau['affectes']:
                        if len(creneau['affectes']) < max_par_date:
                            creneau['affectes'].append(a)
                            compteur[a] += 1
                            affectations[a].append(creneau['dt'])

        # Étape 2 : remplir les créneaux jusqu'au min_par_date
        for creneau in creneaux_info:
            while len(creneau['affectes']) < min_par_date:
                candidats = [n for n in creneau['dispos'] if n not in creneau['affectes']]
                if not candidats:
                    break
                nom = random.choice(candidats)
                creneau['affectes'].append(nom)
                compteur[nom] += 1
                affectations[nom].append(creneau['dt'])

        # =====================================================
        # 8️⃣ Affichage final
        # =====================================================
        st.subheader("Répartition finale")
        for c in sorted(creneaux_info, key=lambda x: x['dt']):
            st.write(f"{c['cle']} → {', '.join(c['affectes']) if c['affectes'] else 'Aucun'}")

        st.subheader("Nombre de créneaux par enfant")
        st.write(compteur)
