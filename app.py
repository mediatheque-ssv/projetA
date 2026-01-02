import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Répartition optimisée des enfants / bénévoles")

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
        st.error(f"Erreur CSV : {e}")
        st.stop()

    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    if not set(["Date", "Horaires", "Noms_dispos"]).issubset(set(df.columns)):
        st.error(f"Colonnes manquantes : {df.columns.tolist()}")
        st.stop()

    st.subheader("Aperçu du CSV")
    st.dataframe(df.head(10))

    # =====================================================
    # 2️⃣ EXTRACTION DES ENFANTS
    # =====================================================
    sample_cell = str(df["Noms_dispos"].iloc[0])
    separator = "," if "," in sample_cell else ";"
    noms_uniques = sorted({
        n.strip() for cell in df["Noms_dispos"] if pd.notna(cell) for n in str(cell).split(separator) if n.strip()
    })

    st.subheader("Enfants détectés")
    st.write(noms_uniques)
    st.info(f"Séparateur détecté : '{separator}'")

    # =====================================================
    # 3️⃣ PARAMÈTRES GÉNÉRAUX
    # =====================================================
    st.subheader("Paramètres de répartition")
    col1, col2 = st.columns(2)
    with col1:
        min_par_date = st.slider("Min enfants par créneau", 1, 10, 4)
        max_par_date = st.slider("Max enfants par créneau", min_par_date, 10, 5)
    with col2:
        delai_minimum = st.slider("Délai minimum entre deux créneaux (jours)", 1, 14, 7)

    # =====================================================
    # 4️⃣ BINÔMES INSÉPARABLES
    # =====================================================
    st.subheader("Binômes inséparables")
    if "binomes" not in st.session_state:
        st.session_state.binomes = []

    col1, col2 = st.columns(2)
    with col1:
        enfant_a = st.selectbox("Enfant A", noms_uniques, key="a")
    with col2:
        enfant_b = st.selectbox("Enfant B", noms_uniques, key="b")
    if enfant_a != enfant_b:
        if st.button("Ajouter le binôme"):
            if (enfant_a, enfant_b) not in st.session_state.binomes and (enfant_b, enfant_a) not in st.session_state.binomes:
                st.session_state.binomes.append((enfant_a, enfant_b))

    if st.session_state.binomes:
        st.write("Binômes définis :")
        for a, b in st.session_state.binomes:
            st.write(f"- {a} + {b}")

    # =====================================================
    # 5️⃣ PARAMÈTRES MIN/MAX PAR ENFANT
    # =====================================================
    st.subheader("Min/max global par enfant")
    min_occ_default = 3
    max_occ_default = 6
    col1, col2 = st.columns(2)
    with col1:
        min_occ_par_enfant = st.number_input("Min présences par enfant", 0, 20, min_occ_default)
    with col2:
        max_occ_par_enfant = st.number_input("Max présences par enfant", min_occ_par_enfant, 20, max_occ_default)

    dispo_totales = {nom: sum(df["Noms_dispos"].apply(lambda x: nom in str(x).split(separator))) for nom in noms_uniques}
    st.write("Disponibilités max selon CSV :", dispo_totales)

    # =====================================================
    # 6️⃣ PARSING DES DATES
    # =====================================================
    mois_fr = {'janvier':1,'février':2,'fevrier':2,'mars':3}

    def parse_dt(row):
        try:
            parts = str(row['Date']).strip().lower().split()
            if len(parts)<3: return pd.Timestamp("1900-01-01")
            day = int(parts[1])
            month = mois_fr.get(parts[2],1)
            year = 2026
            hour = int(str(row['Horaires']).split('h')[0]) if 'h' in str(row['Horaires']) else 0
            return pd.Timestamp(year=year, month=month, day=day, hour=hour)
        except:
            return pd.Timestamp("1900-01-01")

    df['dt'] = df.apply(parse_dt, axis=1)
    df_sorted = df.sort_values("dt")

    # =====================================================
    # 7️⃣ LANCEMENT DE LA RÉPARTITION
    # =====================================================
    if st.button("Lancer la répartition optimisée"):
        # Créneaux
        creneaux_info = []
        for _, row in df_sorted.iterrows():
            if row['dt'] == pd.Timestamp("1900-01-01"): continue
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator) if n.strip() in noms_uniques]
            creneaux_info.append({
                'cle': f"{row['Date']} | {row['Horaires']}",
                'dt': row['dt'],
                'dispos': dispos,
                'affectes': []
            })

        # Compteur par enfant
        compteur = {nom: 0 for nom in noms_uniques}
        affectations = {nom: [] for nom in noms_uniques}

        # Boucle d’affectation
        for _ in range(50):  # itérations pour équilibrer
            for creneau in creneaux_info:
                if len(creneau['affectes']) >= max_par_date: continue

                # Affecter binômes en priorité
                for a,b in st.session_state.binomes:
                    if (a in creneau['dispos'] and b in creneau['dispos'] and
                        a not in creneau['affectes'] and b not in creneau['affectes'] and
                        compteur[a]<max_occ_par_enfant and compteur[b]<max_occ_par_enfant):
                        last_a = affectations[a][-1] if affectations[a] else pd.Timestamp("1900-01-01")
                        last_b = affectations[b][-1] if affectations[b] else pd.Timestamp("1900-01-01")
                        if (creneau['dt']-last_a).days>=delai_minimum and (creneau['dt']-last_b).days>=delai_minimum:
                            creneau['affectes'].extend([a,b])
                            compteur[a]+=1
                            compteur[b]+=1
                            affectations[a].append(creneau['dt'])
                            affectations[b].append(creneau['dt'])

                # Affecter autres enfants
                candidats = sorted(
                    [n for n in creneau['dispos'] if n not in creneau['affectes'] and compteur[n]<max_occ_par_enfant],
                    key=lambda x: compteur[x]
                )
                for nom in candidats:
                    if len(creneau['affectes'])>=max_par_date: break
                    last = affectations[nom][-1] if affectations[nom] else pd.Timestamp("1900-01-01")
                    if (creneau['dt']-last).days>=delai_minimum:
                        creneau['affectes'].append(nom)
                        compteur[nom]+=1
                        affectations[nom].append(creneau['dt'])

        # =====================================================
        # 8️⃣ AFFICHAGE DU PLANNING
        # =====================================================
        st.subheader("Planning final")
        for creneau in creneaux_info:
            st.write(f"{creneau['cle']} → {', '.join(creneau['affectes'])} ({max_par_date-len(creneau['affectes'])} place(s))")

        # =====================================================
        # 9️⃣ STATISTIQUES
        # =====================================================
        st.subheader("Statistiques par enfant")
        moyenne = sum(compteur.values())/len(compteur)
        st.write(f"Moyenne présences/enfant : {moyenne:.1f}")
        sous = [n for n,c in compteur.items() if c<min_occ_par_enfant]
        sur = [n for n,c in compteur.items() if c>max_occ_par_enfant]
        if sous: st.warning(f"Enfants sous-représentés : {', '.join(sous)}")
        if sur: st.warning(f"Enfants sur-représentés : {', '.join(sur)}")

        fig, ax = plt.subplots()
        ax.bar(compteur.keys(), compteur.values())
        ax.axhline(y=moyenne, color='g', linestyle='--', label=f"Moyenne ({moyenne:.1f})")
        ax.axhline(y=min_occ_par_enfant, color='r', linestyle='--', label=f"Min ({min_occ_par_enfant})")
        ax.axhline(y=max_occ_par_enfant, color='orange', linestyle='--', label=f"Max ({max_occ_par_enfant})")
        ax.set_xticklabels(compteur.keys(), rotation=90)
        ax.set_ylabel("Présences")
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
            "Télécharger le planning CSV",
            data=csv,
            file_name="planning_optimise.csv",
            mime="text/csv"
        )
