import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants")

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Noms_dispos)",
    type=["csv"]
)

if not uploaded_file:
    st.stop()

try:
    df = pd.read_csv(
        uploaded_file,
        sep=";",
        encoding="utf-8-sig",
        engine="python"
    )
except Exception as e:
    st.error(f"Erreur de lecture du CSV : {e}")
    st.stop()

# Nettoyage colonnes
df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

# Vérification colonnes
if "Date" not in df.columns or "Noms_dispos" not in df.columns:
    st.error(
        "Le CSV doit contenir EXACTEMENT les colonnes : Date ; Noms_dispos\n"
        f"Colonnes détectées : {df.columns.tolist()}"
    )
    st.stop()

st.subheader("Aperçu du CSV")
st.dataframe(df)

# =====================================================
# 2️⃣ PARAMÈTRES GÉNÉRAUX
# =====================================================
st.subheader("Paramètres généraux")

max_par_date = st.slider(
    "Nombre maximum d'enfants par créneau",
    1, 10, 3
)

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
st.write(noms_uniques if noms_uniques else "Aucun enfant détecté !")

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
st.subheader("Nombre maximal d'occurrences par enfant")

max_occurrences = {}
if noms_uniques:
    for nom in noms_uniques:
        max_occurrences[nom] = st.number_input(
            nom,
            min_value=0,
            max_value=10,
            value=1,
            key=f"occ_{nom}"
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
    dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]

    repartition[date] = []
    deja_affectes_par_date[date] = set()

    # ---- BINÔMES D'ABORD
    for a, b in binomes:
        if (
            a in dispos and b in dispos
            and compteur.get(a, 0) < max_occurrences.get(a, 1)
            and compteur.get(b, 0) < max_occurrences.get(b, 1)
            and len(repartition[date]) <= max_par_date - 2
        ):
            repartition[date].extend([a, b])
            compteur[a] += 1
            compteur[b] += 1
            deja_affectes_par_date[date].update([a, b])

    # ---- ENSUITE LES SOLOS
    for nom in dispos:
        if (
            nom not in deja_affectes_par_date[date]
            and compteur.get(nom, 0) < max_occurrences.get(nom, 1)
            and len(repartition[date]) < max_par_date
        ):
            repartition[date].append(nom)
            compteur[nom] += 1
            deja_affectes_par_date[date].add(nom)

# =====================================================
# 7️⃣ AFFICHAGE
# =====================================================
for date, enfants in repartition.items():
    st.write(
        f"**{date}** : "
        f"{', '.join(enfants) if enfants else 'Aucun'} "
        f"({max_par_date - len(enfants)} place(s) restante(s))"
    )

# =====================================================
# 8️⃣ EXPORT CSV
# =====================================================
export_df = pd.DataFrame([
    {
        "Date": date,
        "Enfants_affectés": ";".join(enfants),
        "Places_restantes": max_par_date - len(enfants)
    }
    for date, enfants in repartition.items()
])

csv = export_df.to_csv(index=False, sep=";").encode("utf-8")

st.download_button(
    "Télécharger la répartition CSV",
    data=csv,
    file_name="repartition.csv",
    mime="text/csv"
)
