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
    # 3️⃣ Paramètres simplifiés
    # =====================================================
    st.subheader("Paramètres")
    min_par_date = st.slider("Nombre minimal d'enfants par créneau", 1, 10, 2)
    max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_par_date, 10, 5)
    delai_minimum = st.slider("Délai minimum entre deux présences (jours)", 1, 14, 7)

    # =====================================================
    # 4️⃣ Gestion des binômes
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
    # 5️⃣ Parsing dates
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
    # 6️⃣ Répartition équilibrée
    # =====================================================
    if st.button("Lancer la répartition"):
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}

        # Trier les enfants par disponibilité (du moins dispo au plus dispo)
        disponibilites_totales = {nom: sum(nom in c['dispos'] for c in creneaux_info) for nom in noms_uniques}
        enfants_trie = sorted(noms_uniques, key=lambda n: disponibilites_totales[n])

        for nom in enfants_trie:
            # Affecter au maximum de créneaux disponibles
            for creneau in creneaux_info:
                if len(creneau['affectes']) >= max_par_date:
                    continue
                if nom not in creneau['dispos'] or nom in creneau['affectes']:
                    continue
                last = affectations[nom][-1] if affectations[nom] else pd.Timestamp("1900-01-01")
                if (creneau['dt'] - last).days < delai_minimum:
                    continue
                # Vérifier binômes
                binome_a_affecte = any(b in creneau['affectes'] for a,b in st.session_state.binomes if a==nom)
                binome_b_affecte = any(a in creneau['affectes'] for a,b in st.session_state.binomes if b==nom)
                if binome_a_affecte or binome_b_affecte:
                    continue
                # Affecter l'enfant
                creneau['affectes'].append(nom)
                compteur[nom] += 1
                affectations[nom].append(creneau['dt'])
                # Affecter le binôme si nécessaire
                for a,b in st.session_state.binomes:
                    if a==nom and b in creneau['dispos'] and b not in creneau['affectes']:
                        creneau['affectes'].append(b)
                        compteur[b] += 1
                        affectations[b].append(creneau['dt'])
                    if b==nom and a in creneau['dispos'] and a not in creneau['affectes']:
                        creneau['affectes'].append(a)
                        compteur[a] += 1
                        affectations[a].append(creneau['dt'])

        # =====================================================
        # 7️⃣ Vérifier le nombre minimal par créneau
        # =====================================================
        for creneau in creneaux_info:
            while len(creneau['affectes']) < min_par_date:
                candidats = [n for n in creneau['dispos'] if n not in creneau['affectes']]
                if not candidats:
                    break
                nom = random.choice(candidats)
                creneau['affectes'].append(nom)
                compteur[nom] += 1

        # =====================================================
        # 8️⃣ Affichage final
        # =====================================================
        st.subheader("Répartition finale")
        for c in sorted(creneaux_info, key=lambda x: x['dt']):
            st.write(f"{c['cle']} → {', '.join(c['affectes']) if c['affectes'] else 'Aucun'}")

        st.subheader("Nombre de créneaux par enfant")
        st.write(compteur)
