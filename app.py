import streamlit as st
import pandas as pd
import random
from datetime import timedelta

st.title("Répartition égalitaire bénévoles / enfants (avec lissage mensuel)")

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
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

if not {"Date", "Horaires", "Noms_dispos"}.issubset(df.columns):
    st.error("Colonnes requises : Date ; Horaires ; Noms_dispos")
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
st.write(noms_uniques)

# =====================================================
# 3️⃣ PARAMÈTRES
# =====================================================
st.subheader("Paramètres des créneaux")

min_par_date = st.slider("Minimum par créneau", 1, 10, 4)
max_par_date = st.slider("Maximum par créneau", min_par_date, 10, max(5, min_par_date))

total_creaneaux = len(df)
places_totales = total_creaneaux * max_par_date
occ_recommandee = round(places_totales / len(noms_uniques))

max_occ_global = st.number_input(
    "Occurrences max par enfant",
    min_value=1,
    max_value=total_creaneaux,
    value=occ_recommandee
)

# =====================================================
# 4️⃣ BINÔMES
# =====================================================
st.subheader("Binômes à ne pas séparer")

if "binomes" not in st.session_state:
    st.session_state.binomes = []

col1, col2 = st.columns(2)
with col1:
    enfant_a = st.selectbox("Enfant A", noms_uniques)
with col2:
    enfant_b = st.selectbox("Enfant B", noms_uniques)

if st.button("Ajouter le binôme"):
    if enfant_a != enfant_b and (enfant_a, enfant_b) not in st.session_state.binomes:
        st.session_state.binomes.append((enfant_a, enfant_b))

if st.session_state.binomes:
    st.write("Binômes définis :")
    for a, b in st.session_state.binomes:
        st.write(f"- {a} + {b}")

binomes = st.session_state.binomes

# =====================================================
# 5️⃣ RÉPARTITION AVEC ESPACEMENT + MALUS MENSUEL
# =====================================================
if st.button("Répartir les enfants"):

    repartition = {}
    compteur = {n: 0 for n in noms_uniques}
    affectations = {n: [] for n in noms_uniques}
    affectations_mois = {n: {} for n in noms_uniques}

    DELAI_PREF = 14
    DELAI_MIN = 7

    # malus mensuel
    MALUS_1 = 10
    MALUS_2 = 30

    def parse_dt(row):
        try:
            return pd.to_datetime(f"{row['Date']} {row['Horaires']}", dayfirst=True)
        except:
            return pd.to_datetime("1900-01-01")

    df_sorted = df.copy()
    df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
    df_sorted = df_sorted.sort_values("dt")

    for _, row in df_sorted.iterrows():
        date = str(row["Date"]).strip()
        horaire = str(row["Horaires"]).strip()
        dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]

        cle = f"{date} | {horaire}"
        repartition[cle] = []

        dt = pd.to_datetime(f"{date} {horaire}", dayfirst=True, errors="coerce")
        if pd.isna(dt):
            dt = pd.to_datetime("1900-01-01")

        mois = dt.strftime("%Y-%m")

        # ---- BINÔMES
        for a, b in random.sample(binomes, len(binomes)):
            if (
                a in dispos and b in dispos
                and compteur[a] < max_occ_global
                and compteur[b] < max_occ_global
                and len(repartition[cle]) <= max_par_date - 2
            ):
                da = min([(dt - d).days for d in affectations[a]] + [999])
                db = min([(dt - d).days for d in affectations[b]] + [999])

                if da >= DELAI_MIN and db >= DELAI_MIN:
                    repartition[cle].extend([a, b])
                    compteur[a] += 1
                    compteur[b] += 1
                    affectations[a].append(dt)
                    affectations[b].append(dt)
                    affectations_mois[a][mois] = affectations_mois[a].get(mois, 0) + 1
                    affectations_mois[b][mois] = affectations_mois[b].get(mois, 0) + 1

        # ---- SOLOS AVEC SCORE
        candidats = []
        for n in dispos:
            if n in repartition[cle] or compteur[n] >= max_occ_global:
                continue

            distance = min([(dt - d).days for d in affectations[n]] + [999])
            if distance < DELAI_MIN:
                continue

            occ_mois = affectations_mois[n].get(mois, 0)
            malus = 0
            if occ_mois == 1:
                malus = MALUS_1
            elif occ_mois >= 2:
                malus = MALUS_2

            score = (
                distance
                - malus
                - compteur[n] * 2
            )

            candidats.append((score, n))

        candidats.sort(reverse=True)

        for _, n in candidats:
            if len(repartition[cle]) < max_par_date:
                repartition[cle].append(n)
                compteur[n] += 1
                affectations[n].append(dt)
                affectations_mois[n][mois] = affectations_mois[n].get(mois, 0) + 1

        # ---- COMPLÉTER JUSQU’À min_par_date
        restants = [n for n in noms_uniques if n not in repartition[cle] and compteur[n] < max_occ_global]
        random.shuffle(restants)

        for n in restants:
            if len(repartition[cle]) < min_par_date:
                repartition[cle].append(n)
                compteur[n] += 1
                affectations[n].append(dt)
                affectations_mois[n][mois] = affectations_mois[n].get(mois, 0) + 1

    # =====================================================
    # 6️⃣ TRI FINAL
    # =====================================================
    def cle_tri(cle):
        parts = cle.split("|", 1)
        date_str = parts[0].strip()
        heure_str = parts[1].strip() if len(parts) > 1 else "00:00"

        date_dt = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
        if pd.isna(date_dt):
            date_dt = pd.to_datetime("1900-01-01")

        heure_dt = pd.to_datetime(heure_str, format="%H:%M", errors="coerce")
        if pd.isna(heure_dt):
            heure_dt = pd.to_datetime("00:00", format="%H:%M")

        return (date_dt, heure_dt)

    repartition = dict(sorted(repartition.items(), key=cle_tri))

    # =====================================================
    # 7️⃣ AFFICHAGE
    # =====================================================
    st.subheader("Répartition finale")
    for cle, enfants in repartition.items():
        st.write(f"{cle} : {', '.join(enfants) if enfants else 'Aucun'}")

    st.subheader("Occurrences totales")
    st.write(dict(sorted(compteur.items())))

    # =====================================================
    # 8️⃣ EXPORT CSV
    # =====================================================
    export_df = pd.DataFrame([
        {
            "Date_Horaire": cle,
            "Enfants_affectés": ";".join(enfants),
            "Places_restantes": max_par_date - len(enfants)
        }
        for cle, enfants in repartition.items()
    ])

    csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button("Télécharger le CSV", csv, "repartition.csv", "text/csv")
