import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants")

# =====================================================
# 1️⃣ IMPORT CSV (ULTRA ROBUSTE)
# =====================================================
uploaded_file = st.file_uploader("Importer le CSV", type=["csv"])
if not uploaded_file:
    st.stop()

try:
    uploaded_file.seek(0)
    df = pd.read_csv(
        uploaded_file,
        sep=None,
        engine="python",
        encoding="utf-8-sig"
    )
except Exception as e:
    st.error(f"Erreur de lecture du CSV : {e}")
    st.stop()

# =====================================================
# 2️⃣ CORRECTION CAS CSV EN 1 SEULE COLONNE
# =====================================================
# Ex: ['ï»¿Date,Horaires,Noms_dispos']
if len(df.columns) == 1 and "," in df.columns[0]:
    df = df.iloc[:, 0].str.split(",", expand=True)

# Nettoyage noms colonnes
df.columns = (
    df.columns
    .astype(str)
    .str.replace("\ufeff", "", regex=False)
    .str.replace("ï»¿", "", regex=False)
    .str.strip()
)

# =====================================================
# 3️⃣ VÉRIFICATION COLONNES
# =====================================================
colonnes_attendues = ["Date", "Horaires", "Noms_dispos"]
if list(df.columns) != colonnes_attendues:
    st.error(
        "Le CSV doit contenir EXACTEMENT les colonnes : "
        + ", ".join(colonnes_attendues)
        + f"\nColonnes détectées : {df.columns.tolist()}"
    )
    st.stop()

st.success("CSV importé correctement ✅")
st.dataframe(df)

# =====================================================
# 4️⃣ PARAMÈTRES
# =====================================================
max_par_creneau = st.slider("Nombre d'enfants par créneau", 1, 10, 3)

# =====================================================
# 5️⃣ EXTRACTION DES ENFANTS
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
# 6️⃣ BINÔMES
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
# 7️⃣ OCCURRENCES MAX PAR MOIS
# =====================================================
st.subheader("Occurrences max par enfant (par mois)")
max_occ = {
    e: st.number_input(e, 0, 10, 1)
    for e in enfants
}

# =====================================================
# 8️⃣ RÉPARTITION
# =====================================================
repartition = {}
compteur = {e: 0 for e in enfants}
presence_jour = {}

for _, row in df.iterrows():
    date = str(row["Date"]).strip()
    horaire = str(row["Horaires"]).strip()
    cle = f"{date} | {horaire}"

    dispos = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]
    repartition[cle] = []
    presence_jour.setdefault(date, set())

    # Binômes
    for a, b in st.session_state.binomes:
        if (
            a in dispos and b in dispos
            and a not in presence_jour[date]
            and b not in presence_jour[date]
            and compteur[a] < max_occ[a]
            and compteur[b] < max_occ[b]
            and len(repartition[cle]) <= max_par_creneau - 2
        ):
            repartition[cle] += [a, b]
            compteur[a] += 1
            compteur[b] += 1
            presence_jour[date].update([a, b])

    # Solos
    for e in dispos:
        if (
            e not in presence_jour[date]
            and compteur[e] < max_occ[e]
            and len(repartition[cle]) < max_par_creneau
        ):
            repartition[cle].append(e)
            compteur[e] += 1
            presence_jour[date].add(e)

# =====================================================
# 9️⃣ AFFICHAGE
# =====================================================
st.subheader("Répartition finale")
for cle, lst in repartition.items():
    st.write(
        f"**{cle}** : "
        f"{', '.join(lst) if lst else 'Aucun'} "
        f"({max_par_creneau - len(lst)} place(s) restante(s))"
    )

# =====================================================
# 🔟 EXPORT
# =====================================================
export_df = pd.DataFrame([
    {
        "Date_Horaire": cle,
        "Enfants": ";".join(lst),
        "Places_restantes": max_par_creneau - len(lst)
    }
    for cle, lst in repartition.items()
])

csv = export_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
st.download_button(
    "Télécharger la répartition CSV",
    data=csv,
    file_name="repartition.csv",
    mime="text/csv"
)
