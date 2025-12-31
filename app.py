import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants")

# =====================================================
# 1️⃣ IMPORT CSV
# =====================================================
uploaded_file = st.file_uploader("Importer le CSV", type=["csv"])
if not uploaded_file:
    st.stop()

# =====================================================
# 2️⃣ LECTURE BRUTE (ON NE FAIT AUCUNE HYPOTHÈSE)
# =====================================================
uploaded_file.seek(0)
raw = uploaded_file.read().decode("utf-8-sig", errors="replace")

lines = raw.splitlines()
if not lines:
    st.error("CSV vide")
    st.stop()

# =====================================================
# 3️⃣ CORRECTION EN-TÊTE EXCEL ONLINE (CAS QUI TE BLOQUE)
# =====================================================
header = lines[0]

# Si l'en-tête est collé en une seule colonne
if header.count(",") == 2:
    sep = ","
elif header.count(";") == 2:
    sep = ";"
else:
    st.error(f"En-tête invalide : {header}")
    st.stop()

# Reconstruction CSV propre
clean_csv = "\n".join(lines)

# =====================================================
# 4️⃣ LECTURE pandas PROPRE
# =====================================================
from io import StringIO

df = pd.read_csv(
    StringIO(clean_csv),
    sep=sep,
    encoding="utf-8"
)

# Nettoyage final colonnes
df.columns = (
    df.columns
    .str.replace("\ufeff", "", regex=False)
    .str.replace("ï»¿", "", regex=False)
    .str.strip()
)

# =====================================================
# 5️⃣ VÉRIFICATION (ENFIN OK)
# =====================================================
colonnes_attendues = ["Date", "Horaires", "Noms_dispos"]
if list(df.columns) != colonnes_attendues:
    st.error(
        "Colonnes attendues : "
        + ", ".join(colonnes_attendues)
        + f"\nColonnes détectées : {df.columns.tolist()}"
    )
    st.stop()

st.success("CSV importé correctement ✅")
st.dataframe(df)
