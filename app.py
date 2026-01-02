import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Répartition enfants", layout="wide")
st.title("Répartition des enfants par créneau")

# =====================================================
# Upload CSV
# =====================================================
uploaded_file = st.file_uploader(
    "Importer le CSV (séparateur ;)",
    type=["csv"]
)

if not uploaded_file:
    st.stop()

# =====================================================
# Lecture CSV robuste
# =====================================================
try:
    df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8")
except Exception:
    df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

# Colonnes attendues
required_cols = {"Date", "Heure", "Enfant"}
if not required_cols.issubset(df.columns):
    st.error(f"Colonnes requises manquantes : {required_cols}")
    st.stop()

df = df.dropna(subset=["Date", "Heure", "Enfant"])
df["Date"] = df["Date"].astype(str).str.strip()
df["Heure"] = df["Heure"].astype(str).str.strip()
df["Enfant"] = df["Enfant"].astype(str).str.strip()

# =====================================================
# Paramètres
# =====================================================
CAPACITE = st.number_input(
    "Capacité par créneau",
    min_value=1,
    max_value=10,
    value=5
)

# =====================================================
# Créneaux
# =====================================================
df["Cle"] = df["Date"] + " | " + df["Heure"]

creneaux = sorted(df["Cle"].unique().tolist())
enfants = sorted(df["Enfant"].unique().tolist())

# =====================================================
# Bouton
# =====================================================
if not st.button("Répartir les enfants"):
    st.stop()

# =====================================================
# Initialisation
# =====================================================
repartition = {c: [] for c in creneaux}
random.shuffle(enfants)

# =====================================================
# Répartition simple (stable)
# =====================================================
idx = 0
for enfant in enfants:
    essais = 0
    while essais < len(creneaux):
        c = creneaux[idx % len(creneaux)]
        if len(repartition[c]) < CAPACITE:
            repartition[c].append(enfant)
            idx += 1
            break
        idx += 1
        essais += 1

# =====================================================
# TRI ROBUSTE (CORRECTION DÉFINITIVE)
# =====================================================
def cle_tri(cle):
    cle = str(cle)  # 🔒 correction clé

    if "|" not in cle:
        return (pd.to_datetime("1900-01-01"), pd.to_datetime("00:00"))

    date_str, heure_str = cle.split("|", 1)
    date_str = date_str.strip()
    heure_str = heure_str.strip()

    date_dt = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
    if pd.isna(date_dt):
        date_dt = pd.to_datetime("1900-01-01")

    heure_dt = pd.to_datetime(heure_str, format="%H:%M", errors="coerce")
    if pd.isna(heure_dt):
        heure_dt = pd.to_datetime("00:00", format="%H:%M")

    return (date_dt, heure_dt)

repartition = dict(sorted(repartition.items(), key=cle_tri))

# =====================================================
# AFFICHAGE
# =====================================================
st.subheader("Répartition finale")

for cle, enfants in repartition.items():
    restants = CAPACITE - len(enfants)
    if enfants:
        st.write(
            f"**{cle}** : {', '.join(enfants)} "
            f"({restants} place(s) restante(s))"
        )
    else:
        st.write(
            f"**{cle}** : Aucun "
            f"({restants} place(s) restante(s))"
        )

# =====================================================
# Stats simples
# =====================================================
st.subheader("Occurrences par enfant")

stats = {}
for enfants in repartition.values():
    for e in enfants:
        stats[e] = stats.get(e, 0) + 1

df_stats = (
    pd.DataFrame.from_dict(stats, orient="index", columns=["Occurrences"])
    .sort_values("Occurrences", ascending=False)
)

st.dataframe(df_stats)
