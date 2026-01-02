import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

st.title("Répartition optimisée des bénévoles/enfants (version finale)")

# =====================================================
# 1️⃣ IMPORT ET VÉRIFICATION DU CSV
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

    # Nettoyage des noms de colonnes
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    if not set(["Date", "Horaires", "Noms_dispos"]).issubset(set(df.columns)):
        st.error(f"Colonnes manquantes. Attendu : Date, Horaires, Noms_dispos. Trouvé : {df.columns.tolist()}")
        st.stop()

    st.subheader("Aperçu du CSV")
    st.dataframe(df.head(10))  # Affiche les 10 premières lignes

    # =====================================================
    # 2️⃣ EXTRACTION DES NOMS ET PARAMÈTRES
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
    # 3️⃣ PARAMÈTRES DE RÉPARTITION
    # =====================================================
    st.subheader("Paramètres de répartition")
    col1, col2 = st.columns(2)
    with col1:
        min_par_date = st.slider("Nombre minimal d'enfants par créneau", 1, 10, 3)
        max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_par_date, 10, 5)
    with col2:
        delai_minimum = st.slider("Délai minimum entre 2 créneaux (jours)", 1, 14, 7)
        max_occ_global = st.number_input("Nombre maximal d'occurrences par enfant", 1, 20, 6)

    # =====================================================
    # 4️⃣ GESTION DES BINÔMES
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
    # 5️⃣ PARAMÈTRES DE PARSE DES DATES (janvier, février, mars)
    # =====================================================
    mois_fr = {
        'janvier': 1,
        'février': 2,
        'mars': 3,
        'fevrier': 2,  # Variante sans accent
    }

    def parse_dt(row):
        try:
            date_str = str(row['Date']).strip().lower()
            horaire_str = str(row['Horaires']).strip()
            parts = date_str.split()
            if len(parts) < 3:
                st.warning(f"Format de date invalide : '{date_str}'")
                return pd.to_datetime("1900-01-01")
            jour = int(parts[1])
            mois_nom = parts[2]
            if mois_nom not in mois_fr:
                st.warning(f"Mois non reconnu : '{mois_nom}' (utilisez janvier/février/mars)")
                return pd.to_datetime("1900-01-01")
            mois = mois_fr[mois_nom]
            annee = 2026
            heure = int(horaire_str.split('h')[0]) if 'h' in horaire_str else 0
            return pd.Timestamp(year=annee, month=mois, day=jour, hour=heure)
        except Exception as e:
            st.warning(f"Erreur de parsing pour '{row['Date']}' : {e}")
            return pd.to_datetime("1900-01-01")

    # =====================================================
    # 6️⃣ LANCEMENT DE LA RÉPARTITION
    # =====================================================
    if st.button("Lancer la répartition optimisée"):
        # Initialisation
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}

        # Parsing et tri des dates
        df['dt'] = df.apply(parse_dt, axis=1)
        df_sorted = df.sort_values("dt")

        # Vérification des mois détectés
        mois_presents = set()
        for _, row in df_sorted.iterrows():
            if row['dt'] != pd.to_datetime("1900-01-01"):
                mois_presents.add(row['dt'].month)
        st.subheader("Mois détectés dans le CSV")
        st.write(f"Mois présents : {sorted([list(mois_fr.keys())[m-1] for m in mois_presents])}")

        # Préparation des créneaux
        creneaux_info = []
        for _, row in df_sorted.iterrows():
            if row['dt'] == pd.to_datetime("1900-01-01"):
                continue
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator) if n.strip() in noms_uniques]
            creneaux_info.append({
                'cle': f"{row['Date']} | {row['Horaires']}",
                'dt': row['dt'],
                'dispos': dispos,
                'affectes': []
            })

        # Date médiane pour équilibrer les affectations
        mid_date = df_sorted['dt'].quantile(0.5)
        max_early_occurrences = max_occ_global // 2

        # =====================================================
        # 7️⃣ ALGORITHME D'AFFECTATION (optimisé)
        # =====================================================
        for _ in range(100):  # 100 itérations pour converger
            for creneau in creneaux_info:
                if len(creneau['affectes']) >= max_par_date:
                    continue

                # Limiter les affectations avant la mi-parcours
                if creneau['dt'] < mid_date:
                    for nom in creneau['dispos'][:]:
                        if compteur[nom] >= max_early_occurrences:
                            creneau['dispos'].remove(nom)

                # Affectation des binômes
                for a, b in st.session_state.binomes:
                    if (a in creneau['dispos'] and b in creneau['dispos'] and
                        a not in creneau['affectes'] and b not in creneau['affectes'] and
                        compteur[a] < max_occ_global and compteur[b] < max_occ_global):
                        last_a = affectations[a][-1] if affectations[a] else pd.Timestamp("1900-01-01")
                        last_b = affectations[b][-1] if affectations[b] else pd.Timestamp("1900-01-01")
                        if (creneau['dt'] - last_a).days >= delai_minimum and (creneau['dt'] - last_b).days >= delai_minimum:
                            creneau['affectes'].extend([a, b])
                            compteur[a] += 1
                            compteur[b] += 1
                            affectations[a].append(creneau['dt'])
                            affectations[b].append(creneau['dt'])

                # Affectation solo (priorité aux moins affectés)
                candidats = sorted(
                    [n for n in creneau['dispos'] if n not in creneau['affectes'] and compteur[n] < max_occ_global],
                    key=lambda x: compteur[x]
                )
                for nom in candidats:
                    if len(creneau['affectes']) >= max_par_date:
                        break
                    last = affectations[nom][-1] if affectations[nom] else pd.Timestamp("1900-01-01")
                    if (creneau['dt'] - last).days >= delai_minimum:
                        creneau['affectes'].append(nom)
                        compteur[nom] += 1
                        affectations[nom].append(creneau['dt'])

        # =====================================================
        # 8️⃣ REMPLIR LES CRÉNEAUX VIDES (surtout mars)
        # =====================================================
        for creneau in creneaux_info:
            if len(creneau['affectes']) < min_par_date:
                candidats = [n for n in creneau['dispos'] if n not in creneau['affectes']]
                random.shuffle(candidats)  # Mélanger pour équité
                for nom in candidats:
                    if len(creneau['affectes']) >= min_par_date:
                        break
                    creneau['affectes'].append(nom)
                    compteur[nom] += 1
                    if creneau['dt'].month == 3:  # Mars
                        st.warning(f"{nom} ajouté·e à {creneau['cle']} pour remplir mars")

        # =====================================================
        # 9️⃣ AFFICHAGE DES RÉSULTATS
        # =====================================================
        st.subheader("Répartition finale optimisée")
        for creneau in sorted(creneaux_info, key=lambda x: x['dt']):
            st.write(f"{creneau['cle']} → {creneau['dt'].strftime('%d/%m')}: {', '.join(creneau['affectes']) if creneau['affectes'] else 'Aucun'} ({max_par_date - len(creneau['affectes'])} place(s))")

        # =====================================================
        # 10️⃣ STATISTIQUES ET EXPORT
        # =====================================================
        st.subheader("Statistiques")
        moyenne = sum(compteur.values()) / len(compteur)
        st.write(f"Moyenne d'affectations/enfant : {moyenne:.1f}")
        sous_representes = [n for n, c in compteur.items() if c < moyenne - 1]
        sur_representes = [n for n, c in compteur.items() if c > moyenne + 1]
        if sous_representes:
            st.warning(f"Enfants sous-représentés : {', '.join(sous_representes)}")
        if sur_representes:
            st.warning(f"Enfants sur-représentés : {', '.join(sur_representes)}")

        # Visualisation
        fig, ax = plt.subplots()
        ax.bar(compteur.keys(), compteur.values())
        ax.axhline(y=moyenne, color='r', linestyle='--', label=f"Moyenne ({moyenne:.1f})")
        ax.set_xticklabels(compteur.keys(), rotation=90)
        ax.set_ylabel("Nombre d'affectations")
        ax.legend()
        st.pyplot(fig)

        # Export CSV
        export_df = pd.DataFrame([{
            "Date_Horaire": c['cle'],
            "Enfants_affectés": ", ".join(c['affectes']),
            "Places_restantes": max_par_date - len(c['affectes'])
        } for c in creneaux_info])
        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Télécharger la répartition CSV",
            data=csv,
            file_name="repartition_optimisee.csv",
            mime="text/csv"
        )
