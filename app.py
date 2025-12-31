import streamlit as st
import pandas as pd
from collections import defaultdict
import random

st.title("Répartition bénévoles / enfants")

# ================== 1️⃣ Import CSV ==================
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

# ================== 2️⃣ Paramètres ==================
st.subheader("Paramètres généraux")

# Max enfants par créneau
max_par_creneau = st.number_input("Nombre maximum d'enfants par créneau", min_value=1, max_value=10, value=3, step=1)

# Extraction des enfants uniques
enfants = sorted({n.strip() for cell in df["Noms_dispos"] for n in str(cell).split(";") if n.strip()})
st.subheader("Enfants détectés")
st.write(enfants)

# ================== 3️⃣ Binômes ==================
st.subheader("Binômes inséparables")
if "binomes" not in st.session_state:
    st.session_state.binomes = []

col1, col2 = st.columns(2)
with col1:
    enfant_a = st.selectbox("Enfant A", enfants, key="a")
with col2:
    enfant_b = st.selectbox("Enfant B", enfants, key="b")

if st.button("Ajouter le binôme") and enfant_a != enfant_b:
    if (enfant_a, enfant_b) not in st.session_state.binomes and (enfant_b, enfant_a) not in st.session_state.binomes:
        st.session_state.binomes.append((enfant_a, enfant_b))

if st.session_state.binomes:
    st.write("Binômes actuels :")
    for x,y in st.session_state.binomes:
        st.write(f"- {x} + {y}")

# ================== 4️⃣ Occurrences max ==================
st.subheader("Nombre maximal d'occurrences par enfant (par mois)")
max_occ = {e: st.number_input(e, min_value=0, max_value=10, value=1, key=f"occ_{e}") for e in enfants}

# ================== 5️⃣ Bouton pour répartir ==================
def calcul_repartition(df, max_par_creneau, max_occ, binomes):
    repartition = {}
    compteur = {e:0 for e in enfants}
    presence_jour = defaultdict(set)

    # On peut mélanger les lignes pour équilibrer
    df_shuffled = df.sample(frac=1, random_state=random.randint(0,1000)).reset_index(drop=True)

    for _, row in df_shuffled.iterrows():
        date = str(row["Date"]).strip()
        horaire = str(row["Horaires"]).strip()
        cle = f"{date} | {horaire}"
        dispo = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]
        repartition[cle] = []

        # Binômes
        for x,y in binomes:
            if (x in dispo and y in dispo and
                x not in presence_jour[date] and y not in presence_jour[date] and
                compteur[x] < max_occ[x] and compteur[y] < max_occ[y] and
                len(repartition[cle]) <= max_par_creneau-2):
                repartition[cle] += [x,y]
                compteur[x] +=1
                compteur[y] +=1
                presence_jour[date].update([x,y])

        # Solos
        random.shuffle(dispo)
        for e in dispo:
            if (e not in presence_jour[date] and compteur[e] < max_occ[e] and len(repartition[cle]) < max_par_creneau):
                repartition[cle].append(e)
                compteur[e] +=1
                presence_jour[date].add(e)

    non_affectes = [e for e,c in compteur.items() if c < max_occ[e]]
    return repartition, non_affectes

# Bouton principal pour répartir
if st.button("Répartir les enfants"):
    repartition, non_affectes = calcul_repartition(df, max_par_creneau, max_occ, st.session_state.binomes)

    # ================== 6️⃣ Affichage ==================
    st.subheader("Répartition finale")
    for cle, lst in repartition.items():
        st.write(f"**{cle}** : {', '.join(lst) if lst else 'Aucun'} ({max_par_creneau - len(lst)} place(s) restante(s))")

    if non_affectes:
        st.subheader("Enfants non affectés")
        st.write(", ".join(non_affectes))

    # ================== 7️⃣ Export CSV ==================
    export_df = pd.DataFrame([
        {"Date_Horaire": cle, "Enfants": ";".join(lst), "Places_restantes": max_par_creneau - len(lst)}
        for cle,lst in repartition.items()
    ])
    csv = export_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button("Télécharger la répartition CSV", data=csv, file_name="repartition.csv", mime="text/csv")
