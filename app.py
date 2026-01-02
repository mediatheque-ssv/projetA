import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

st.set_page_config(page_title="Répartition équilibrée", layout="wide")
st.title("Répartition équilibrée des bénévoles/enfants")

# =====================================================
# 1️⃣ Import CSV
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
    if not set(["Date", "Horaires", "Noms_dispos"]).issubset(df.columns):
        st.error(f"Colonnes manquantes. Attendu : Date, Horaires, Noms_dispos. Trouvé : {df.columns.tolist()}")
        st.stop()

    st.subheader("Aperçu du CSV")
    st.dataframe(df.head(10))

    # =====================================================
    # 2️⃣ Détection des enfants uniques
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
    # 3️⃣ Paramètres min/max par créneau et par enfant
    # =====================================================
    st.subheader("Paramètres de répartition")
    col1, col2 = st.columns(2)
    with col1:
        min_par_creneau = st.slider("Nombre minimal d'enfants par créneau", 1, 10, 5)
        max_par_creneau = st.slider("Nombre maximal d'enfants par créneau", min_par_creneau, 10, 6)
    with col2:
        min_par_enfant = {}
        max_par_enfant = {}
        st.markdown("**Occurrences par enfant**")
        for nom in noms_uniques:
            dispo_max = sum(df["Noms_dispos"].apply(lambda x: nom in str(x)))
            min_par_enfant[nom] = st.number_input(f"{nom} - min", 0, dispo_max, 1, key=f"min_{nom}")
            max_par_enfant[nom] = st.number_input(f"{nom} - max", min_par_enfant[nom], dispo_max, dispo_max, key=f"max_{nom}")
            st.caption(f"Dispo max selon CSV : {dispo_max}")

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
    # 5️⃣ Parsing des dates
    # =====================================================
    mois_fr = {'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3}

    def parse_dt(row):
        date_str = str(row['Date']).strip().lower()
        horaire_str = str(row['Horaires']).strip()
        try:
            parts = date_str.split()
            jour = int(parts[1])
            mois = mois_fr.get(parts[2], 1)
            annee = 2026
            heure = int(horaire_str.split('h')[0]) if 'h' in horaire_str else 0
            return pd.Timestamp(year=annee, month=mois, day=jour, hour=heure)
        except:
            return pd.Timestamp("1900-01-01")

    df['dt'] = df.apply(parse_dt, axis=1)
    df_sorted = df.sort_values("dt")

    # =====================================================
    # 6️⃣ Préparation des créneaux
    # =====================================================
    creneaux_info = []
    for _, row in df_sorted.iterrows():
        if row['dt'] == pd.Timestamp("1900-01-01"):
            continue
        dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator) if n.strip() in noms_uniques]
        creneaux_info.append({
            'cle': f"{row['Date']} | {row['Horaires']}",
            'dt': row['dt'],
            'dispos': dispos,
            'affectes': []
        })

    # =====================================================
    # 7️⃣ Répartition optimisée
    # =====================================================
    if st.button("Lancer la répartition optimisée"):
        compteur = {nom: 0 for nom in noms_uniques}

        # On remplit par enfant sous-représenté
        enfants_sorted = sorted(noms_uniques, key=lambda n: sum(n in c['dispos'] for c in creneaux_info))
        for nom in enfants_sorted:
            creneaux_disponibles = [c for c in creneaux_info if nom in c['dispos']]
            random.shuffle(creneaux_disponibles)
            for creneau in creneaux_disponibles:
                if compteur[nom] >= min_par_enfant[nom]:
                    break
                if len(creneau['affectes']) >= max_par_creneau:
                    continue
                # Ajouter le binôme si nécessaire
                for a, b in st.session_state.binomes:
                    if nom in [a, b]:
                        partner = b if a == nom else a
                        if partner in creneau['dispos'] and partner not in creneau['affectes']:
                            if len(creneau['affectes']) + 2 <= max_par_creneau:
                                creneau['affectes'].append(nom)
                                creneau['affectes'].append(partner)
                                compteur[nom] += 1
                                compteur[partner] += 1
                                break
                else:
                    if nom not in creneau['affectes']:
                        creneau['affectes'].append(nom)
                        compteur[nom] += 1

        # Remplir les créneaux restants en respectant max par enfant et par créneau
        for creneau in creneaux_info:
            candidats = [n for n in creneau['dispos'] if n not in creneau['affectes'] and compteur[n] < max_par_enfant[n]]
            random.shuffle(candidats)
            while len(creneau['affectes']) < min_par_creneau and candidats:
                n = candidats.pop()
                creneau['affectes'].append(n)
                compteur[n] += 1

        # =====================================================
        # 8️⃣ Affichage du planning final
        # =====================================================
        st.subheader("Planning final")
        for c in sorted(creneaux_info, key=lambda x: x['dt']):
            st.write(f"{c['cle']} → {', '.join(c['affectes']) if c['affectes'] else '(vide)'} ({max_par_creneau - len(c['affectes'])} place(s))")

        # =====================================================
        # 9️⃣ Statistiques
        # =====================================================
        st.subheader("Occurrences par enfant")
        for nom in noms_uniques:
            st.write(f"{nom} : {compteur[nom]}")

        fig, ax = plt.subplots()
        ax.bar(compteur.keys(), compteur.values())
        ax.set_ylabel("Nombre d'occurrences")
        ax.set_xticklabels(compteur.keys(), rotation=90)
        st.pyplot(fig)

        # =====================================================
        # 10️⃣ Export CSV
        # =====================================================
        export_df = pd.DataFrame([{
            "Date_Horaire": c['cle'],
            "Enfants_affectés": ", ".join(c['affectes']),
            "Places_restantes": max_par_creneau - len(c['affectes'])
        } for c in creneaux_info])
        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button("Télécharger le CSV", data=csv,
                           file_name="repartition_equilibree.csv",
                           mime="text/csv")
