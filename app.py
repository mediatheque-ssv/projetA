import streamlit as st
import pandas as pd
from io import StringIO
from collections import defaultdict
import random

st.title("Répartition bénévoles / enfants")

# =====================================================
# 1️⃣ IMPORT CSV ROBUSTE
# =====================================================
uploaded_file = st.file_uploader("Importer le CSV", type=["csv"])
if not uploaded_file:
    st.stop()

uploaded_file.seek(0)
df_raw = pd.read_csv(uploaded_file, header=None, encoding="utf-8-sig")

# Split si tout dans une colonne
if df_raw.shape[1] == 1:
    df = df_raw[0].astype(str).str.split(",", expand=True)
else:
    df = df_raw.copy()

# Supprimer ligne d'en-tête Excel
df = df.iloc[1:].reset_index(drop=True)
df.columns = ["Date", "Horaires", "Noms_dispos"]

st.success("CSV importé correctement ✅")
st.dataframe(df)

# =====================================================
# 2️⃣ PARAMÈTRES
# =====================================================
st.subheader("Paramètres généraux")
max_par_creneau = st.slider("Nombre d'enfants par créneau", 1, 10, 3)

# =====================================================
# 3️⃣ EXTRACTION DES ENFANTS
# =====================================================
enfants = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    for n in str(cell).split(";")
    if n.strip()
})

st.subheader("Enfants détectés")
st.write(enfants)

# =====================================================
# 4️⃣ BINÔMES
# =====================================================
st.subheader("Binômes inséparables")
if "binomes" not in st.session_state:
    st.session_state.binomes = []

col1, col2 = st.columns(2)
with col1:
    a = st.selectbox("Enfant A", enfants)
with col2:
    b = st.selectbox("Enfant B", enfants)

if st.button("Ajouter le binôme") and a != b:
    if (a, b) not in st.session_state.binomes and (b, a) not in st.session_state.binomes:
        st.session_state.binomes.append((a, b))

for a, b in st.session_state.binomes:
    st.write(f"- {a} + {b}")

# =====================================================
# 5️⃣ OCCURRENCES MAX PAR MOIS
# =====================================================
st.subheader("Occurrences max par enfant (par mois)")
max_occ = {e: st.number_input(e, 0, 10, 1) for e in enfants}

# =====================================================
# 6️⃣ RÉPARTITION AUTOMATIQUE
# =====================================================
def calcul_repartition(df, max_par_creneau, max_occ, binomes):
    repartition = {}
    compteur = {e: 0 for e in enfants}
    presence_jour = defaultdict(set)  # empêche deux créneaux le même jour

    # Mélanger l'ordre pour plus d'équilibre
    df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

    for _, row in df_shuffled.iterrows():
        date = str(row["Date"]).strip()
        horaire = str(row["Horaires"]).strip()
        cle = f"{date} | {horaire}"

        dispo = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]
        repartition[cle] = []

        # --- Binômes d'abord
        for x, y in binomes:
            if (
                x in dispo and y in dispo
                and x not in presence_jour[date]
                and y not in presence_jour[date]
                and compteur[x] < max_occ[x]
                and compteur[y] < max_occ[y]
                and len(repartition[cle]) <= max_par_creneau - 2
            ):
                repartition[cle] += [x, y]
                compteur[x] += 1
                compteur[y] += 1
                presence_jour[date].update([x, y])

        # --- Solos ensuite
        random.shuffle(dispo)
        for e in dispo:
            if (
                e not in presence_jour[date]
                and compteur[e] < max_occ[e]
                and len(repartition[cle]) < max_par_creneau
            ):
                repartition[cle].append(e)
                compteur[e] += 1
                presence_jour[date].add(e)

    # Enfants non affectés
    non_affectes = [e for e, c in compteur.items() if c < max_occ[e]]
    return repartition, non_affectes

# Bouton pour recalculer autrement
if st.button("Recalculer la répartition"):
    repartition, non_affectes = calcul_repartition(df, max_par_creneau, max_occ, st.session_state.binomes)

    # =====================================================
    # 7️⃣ AFFICHAGE
    # =====================================================
    st.subheader("Répartition finale")
    for cle, lst in repartition.items():
        st.write(
            f"**{cle}** : {', '.join(lst) if lst else 'Aucun'} "
            f"({max_par_creneau - len(lst)} place(s) restante(s))"
        )

    if non_affectes:
        st.subheader("Enfants non affectés")
        st.write(", ".join(non_affectes))

    # =====================================================
    # 8️⃣ EXPORT CSV
    # =====================================================
    export_df = pd.DataFrame([
        {"Date_Horaire": cle, "Enfants": ";".join(lst), "Places_restantes": max_par_creneau - len(lst)}
        for cle, lst in repartition.items()
    ])

    csv = export_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "Télécharger la répartition CSV",
        data=csv,
        file_name="repartition.csv",
        mime="text/csv"
    )
