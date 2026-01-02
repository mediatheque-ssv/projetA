import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

st.title("Répartition améliorée bénévoles / enfants")

uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if not uploaded_file:
    st.stop()

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

# --- Extraire noms uniques
noms_uniques = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    for n in str(cell).split(";")
    if n.strip()
})

if noms_uniques:
    st.subheader("Enfants détectés")
    st.write(noms_uniques)

# --- Paramètres
if noms_uniques:
    st.subheader("Paramètres des créneaux")
    min_par_date = st.slider("Nombre minimal d'enfants par créneau", 1, 10, 4)
    max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_par_date, 10, max(5, min_par_date))
    total_creaneaux = len(df)
    places_totales = total_creaneaux * max_par_date
    occ_recommandee = round(places_totales / len(noms_uniques))
    max_occ_global = st.number_input(
        "Nombre maximal d'occurrences par enfant (pour tous)",
        1, total_creaneaux, occ_recommandee
    )

# --- Binômes
st.subheader("Binômes à ne pas séparer")
if "binomes" not in st.session_state:
    st.session_state.binomes = []

if noms_uniques:
    col1, col2 = st.columns(2)
    with col1:
        enfant_a = st.selectbox("Enfant A", noms_uniques, key="a")
    with col2:
        enfant_b = st.selectbox("Enfant B", noms_uniques, key="b")
    if enfant_a != enfant_b and st.button("Ajouter le binôme"):
        if (enfant_a, enfant_b) not in st.session_state.binomes and (enfant_b, enfant_a) not in st.session_state.binomes:
            st.session_state.binomes.append((enfant_a, enfant_b))

binomes = st.session_state.binomes

# =====================================================
# --- Fonction pour parser les dates françaises
# =====================================================
def parse_date_fr(date_str, default_year=2026):
    # Exemple : "mercredi 7 janvier" → "7 janvier 2026"
    parts = date_str.split()
    day = parts[1]
    month = parts[2]
    try:
        dt = datetime.strptime(f"{day} {month} {default_year}", "%d %B %Y")
    except:
        dt = pd.NaT
    return dt

# --- Répartition
if st.button("Répartir les enfants"):

    df["Date_dt"] = df["Date"].apply(parse_date_fr)
    df_sorted = df.sort_values("Date_dt").reset_index(drop=True)

    repartition = {}
    compteur = {nom: 0 for nom in noms_uniques}
    dernier_creneau = {nom: pd.Timestamp.min for nom in noms_uniques}

    for _, row in df_sorted.iterrows():
        date = row["Date_dt"]
        if pd.isna(date):
            continue
        horaire = str(row["Horaires"]).strip()
        dispo = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]
        cle = f"{date.strftime('%d/%m/%Y')} | {horaire}"
        repartition[cle] = []
        deja_affectes = set()

        # --- Ajouter binômes
        binomes_dispos = [
            (a, b) for a, b in binomes
            if a in dispo and b in dispo
            and compteur[a] < max_occ_global
            and compteur[b] < max_occ_global
            and (date - dernier_creneau[a]).days >= 14
            and (date - dernier_creneau[b]).days >= 14
            and len(repartition[cle]) <= max_par_date - 2
        ]
        random.shuffle(binomes_dispos)
        for a, b in binomes_dispos:
            repartition[cle].extend([a, b])
            compteur[a] += 1
            compteur[b] += 1
            dernier_creneau[a] = date
            dernier_creneau[b] = date
            deja_affectes.update([a, b])

        # --- Ajouter solos
        solos_dispos = [
            n for n in dispo
            if n not in deja_affectes
            and compteur[n] < max_occ_global
            and (date - dernier_creneau[n]).days >= 14
        ]
        solos_dispos.sort(key=lambda x: compteur[x])
        for n in solos_dispos:
            if len(repartition[cle]) < max_par_date:
                repartition[cle].append(n)
                compteur[n] += 1
                dernier_creneau[n] = date
                deja_affectes.add(n)

        # --- Vérification min_par_date
        if len(repartition[cle]) < min_par_date:
            restants = [n for n in noms_uniques if n not in deja_affectes and compteur[n] < max_occ_global]
            random.shuffle(restants)
            for n in restants:
                if len(repartition[cle]) < min_par_date:
                    repartition[cle].append(n)
                    compteur[n] += 1
                    dernier_creneau[n] = date
                    deja_affectes.add(n)

    # --- Tri final
    def cle_tri(cle_str):
        date_str, horaire_str = cle_str.split("|")
        try:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y"), horaire_str.strip()
        except:
            return datetime.max, horaire_str.strip()

    repartition_tri = dict(sorted(repartition.items(), key=cle_tri))

    # --- Affichage
    st.subheader("Répartition finale")
    for cle, enfants in repartition_tri.items():
        st.write(f"{cle} : {', '.join(enfants)} ({max_par_date - len(enfants)} place(s) restante(s))")

    st.subheader("Occurrences par enfant")
    st.write(dict(sorted(compteur.items())))
