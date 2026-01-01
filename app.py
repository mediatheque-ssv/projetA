import streamlit as st
import pandas as pd
from collections import defaultdict
import random

st.title("Répartition bénévoles / enfants")

# ================== 1️⃣ Import CSV ==================
uploaded_file = st.file_uploader("Importer le CSV", type=["csv"])
if not uploaded_file:
    st.stop()

# Lecture CSV robuste
uploaded_file.seek(0)
df_raw = pd.read_csv(uploaded_file, header=None, encoding="utf-8-sig")

# Si tout est dans une colonne, on sépare par virgule
if df_raw.shape[1] == 1:
    df = df_raw[0].astype(str).str.split(",", expand=True)
else:
    df = df_raw.copy()

# Supprimer ligne d'en-tête si nécessaire
df = df.iloc[1:].reset_index(drop=True)
df.columns = ["Date", "Horaires", "Noms_dispos"]

# Nettoyage des colonnes
df["Date"] = df["Date"].astype(str).str.strip()
df["Horaires"] = df["Horaires"].astype(str).str.strip()
df["Noms_dispos"] = df["Noms_dispos"].astype(str).str.strip()

st.success("CSV importé correctement ✅")
st.dataframe(df)

# ================== 2️⃣ Enfants uniques ==================
enfants = sorted({n.strip() for cell in df["Noms_dispos"] for n in str(cell).split(";") if n.strip()})
st.subheader("Enfants détectés")
st.write(enfants)

# ================== 3️⃣ Gestion des binômes ==================
st.subheader("Binômes inséparables")

if "binomes" not in st.session_state:
    st.session_state.binomes = []

col1, col2 = st.columns(2)
with col1:
    enfant_a = st.selectbox("Enfant A", enfants)
with col2:
    enfant_b = st.selectbox("Enfant B", enfants)

if st.button("Ajouter ce binôme"):
    if enfant_a != enfant_b:
        if (enfant_a, enfant_b) not in st.session_state.binomes and (enfant_b, enfant_a) not in st.session_state.binomes:
            st.session_state.binomes.append((enfant_a, enfant_b))

if st.session_state.binomes:
    st.write("Binômes ajoutés :")
    for x, y in st.session_state.binomes:
        st.write(f"- {x} + {y}")

# ================== 4️⃣ Formulaire paramètres ==================
with st.form("param_form"):
    st.subheader("Paramètres de répartition")

    max_par_creneau = st.number_input(
        "Nombre maximum d'enfants par créneau", min_value=1, max_value=10, value=3, step=1
    )
    
    max_occ_global = st.number_input(
        "Nombre maximal d'occurrences par enfant (par mois)", min_value=0, max_value=10, value=1, step=1
    )

    submit_button = st.form_submit_button("Répartir les enfants")

# ================== 5️⃣ Calcul répartition ==================
def calcul_repartition(df, max_par_creneau, max_occ_global, binomes):
    repartition = {}
    compteur = {e: 0 for e in enfants}
    presence_jour = defaultdict(set)

    # Mélange pour éviter toujours le même ordre
    df_shuffled = df.sample(frac=1, random_state=random.randint(0, 1000)).reset_index(drop=True)

    for _, row in df_shuffled.iterrows():
        date = row["Date"]
        horaire = row["Horaires"]
        cle = f"{date} | {horaire}"
        dispo = [n.strip() for n in row["Noms_dispos"].split(";") if n.strip()]
        repartition[cle] = []

        # Binômes
        for x, y in binomes:
            if (
                x in dispo and y in dispo
                and x not in presence_jour[date] and y not in presence_jour[date]
                and compteur[x] < max_occ_global and compteur[y] < max_occ_global
                and len(repartition[cle]) <= max_par_creneau - 2
            ):
                repartition[cle] += [x, y]
                compteur[x] += 1
                compteur[y] += 1
                presence_jour[date].update([x, y])

        # Solos
        random.shuffle(dispo)
        for e in dispo:
            if (
                e not in presence_jour[date]
                and compteur[e] < max_occ_global
                and len(repartition[cle]) < max_par_creneau
            ):
                repartition[cle].append(e)
                compteur[e] += 1
                presence_jour[date].add(e)

    non_affectes = [e for e, c in compteur.items() if c < max_occ_global]
    return repartition, non_affectes

# ================== 6️⃣ Affichage et export ==================
if submit_button:
    repartition, non_affectes = calcul_repartition(df, max_par_creneau, max_occ_global, st.session_state.binomes)

    # Création DataFrame à partir de la répartition
    temp_df = pd.DataFrame([
        {
            "Date": cle.split(" | ")[0].strip(),
            "Horaire": cle.split(" | ")[1].strip(),
            "Enfants": repartition[cle]
        }
        for cle in repartition.keys()
    ])

    # Conversion date en datetime pour tri
    temp_df["Date_parsed"] = pd.to_datetime(temp_df["Date"], dayfirst=True, errors='coerce')

    # Tri par date puis horaire
    temp_df = temp_df.sort_values(by=["Date_parsed", "Horaire"])

    # ================== Affichage trié ==================
    st.subheader("Répartition finale (triée par date)")
    for idx, row in temp_df.iterrows():
        enfants_du_creneau = row["Enfants"]
        places_restantes = max_par_creneau - len(enfants_du_creneau)
        st.write(f"**{row['Date']} | {row['Horaire']}** : "
                 f"{', '.join(enfants_du_creneau) if enfants_du_creneau else 'Aucun'} "
                 f"({places_restantes} place(s) restante(s))")

    if non_affectes:
        st.subheader("Enfants non affectés")
        st.write(", ".join(non_affectes))

    # ================== Export CSV trié ==================
    export_df = pd.DataFrame([
        {
            "Date_Horaire": f"{row['Date']} | {row['Horaire']}",
            "Enfants": ";".join(row["Enfants"]),
            "Places_restantes": max_par_creneau - len(row["Enfants"])
        }
        for idx, row in temp_df.iterrows()
    ])
    csv = export_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button("Télécharger la répartition CSV", data=csv, file_name="repartition.csv", mime="text/csv")
