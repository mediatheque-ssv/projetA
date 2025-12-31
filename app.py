import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants")

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if not uploaded_file:
    st.stop()

# Lecture CSV robuste (UTF-8 ou Latin1)
try:
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1", engine="python")
except Exception as e:
    st.error(f"Impossible de lire le CSV : {e}")
    st.stop()

# Nettoyage colonnes
df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

# Vérification colonnes
required_cols = ["Date", "Horaires", "Noms_dispos"]
if not all(col in df.columns for col in required_cols):
    st.error(
        f"Le CSV doit contenir EXACTEMENT les colonnes : {', '.join(required_cols)}\n"
        f"Colonnes détectées : {df.columns.tolist()}"
    )
    st.stop()

st.subheader("Aperçu du CSV")
st.dataframe(df)

# =====================================================
# 2️⃣ PARAMÈTRES GÉNÉRAUX
# =====================================================
st.subheader("Paramètres généraux")
max_par_creneau = st.slider("Nombre maximum d'enfants par créneau", 1, 10, 3)

# =====================================================
# 3️⃣ EXTRACTION DES NOMS
# =====================================================
noms_uniques = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    for n in str(cell).split(";")
    if n.strip()
})

st.subheader("Enfants détectés")
st.write(noms_uniques)

# =====================================================
# 4️⃣ BINÔMES (INTERFACE)
# =====================================================
st.subheader("Binômes à ne pas séparer")
if "binomes" not in st.session_state:
    st.session_state.binomes = []

if noms_uniques:
    col1, col2 = st.columns(2)
    with col1:
        enfant_a = st.selectbox("Enfant A", noms_uniques, key="a")
    with col2:
        enfant_b = st.selectbox("Enfant B", noms_uniques, key="b")

    if (
        enfant_a != enfant_b
        and st.button("Ajouter le binôme")
        and (enfant_a, enfant_b) not in st.session_state.binomes
        and (enfant_b, enfant_a) not in st.session_state.binomes
    ):
        st.session_state.binomes.append((enfant_a, enfant_b))

if st.session_state.binomes:
    st.write("Binômes définis :")
    for a, b in st.session_state.binomes:
        st.write(f"- {a} + {b}")

binomes = st.session_state.binomes

# =====================================================
# 5️⃣ OCCURRENCES MAXIMALES PAR ENFANT
# =====================================================
st.subheader("Nombre maximal d'occurrences par enfant (par mois)")
max_occurrences = {}
for nom in noms_uniques:
    max_occurrences[nom] = st.number_input(
        nom, min_value=0, max_value=10, value=1, key=f"occ_{nom}"
    )

# =====================================================
# 6️⃣ RÉPARTITION
# =====================================================
st.subheader("Répartition finale")
repartition = {}
compteur = {nom: 0 for nom in noms_uniques}
deja_affectes_par_date = {}

for _, row in df.iterrows():
    date = str(row["Date"]).strip()
    horaire = str(row["Horaires"]).strip()
    creneau = f"{date} {horaire}"
    dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]

    repartition[creneau] = []
    if date not in deja_affectes_par_date:
        deja_affectes_par_date[date] = set()

    # ---- BINÔMES D'ABORD
    for a, b in binomes:
        if (
            a in dispos and b in dispos
            and compteur.get(a, 0) < max_occurrences.get(a, 1)
            and compteur.get(b, 0) < max_occurrences.get(b, 1)
            and len(repartition[creneau]) <= max_par_creneau - 2
            and a not in deja_affectes_par_date[date]
            and b not in deja_affectes_par_date[date]
        ):
            repartition[creneau].extend([a, b])
            compteur[a] += 1
            compteur[b] += 1
            deja_affectes_par_date[date].update([a, b])

    # ---- ENSUITE LES SOLOS
    for nom in dispos:
        if (
            nom not in deja_affectes_par_date[date]
            and compteur.get(nom, 0) < max_occurrences.get(nom, 1)
            and len(repartition[creneau]) < max_par_creneau
        ):
            repartition[creneau].append(nom)
            compteur[nom] += 1
            deja_affectes_par_date[date].add(nom)

# =====================================================
# 7️⃣ AFFICHAGE
# =====================================================
for creneau, enfants in repartition.items():
    st.write(
        f"**{creneau}** : "
        f"{', '.join(enfants) if enfants else 'Aucun'} "
        f"({max_par_creneau - len(enfants)} place(s) restante(s))"
    )

# Enfants non affectés
non_affectes = [nom for nom, c in compteur.items() if c < max_occurrences.get(nom, 1)]
if non_affectes:
    st.subheader("Enfants non affectés")
    st.write(", ".join(non_affectes))

# =====================================================
# 8️⃣ EXPORT CSV
# =====================================================
export_df = pd.DataFrame([
    {
        "Date_Horaire": creneau,
        "Enfants_affectés": ";".join(enfants),
        "Places_restantes": max_par_creneau - len(enfants)
    }
    for creneau, enfants in repartition.items()
])

csv = export_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
st.download_button(
    "Télécharger la répartition CSV",
    data=csv,
    file_name="repartition.csv",
    mime="text/csv"
)
