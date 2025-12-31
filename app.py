import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants")

uploaded_file = st.file_uploader("Importer le CSV", type=["csv"])
if not uploaded_file:
    st.stop()

# =====================================================
# LECTURE CSV ROBUSTE (Excel Online / LibreOffice / Windows)
# =====================================================
try:
    uploaded_file.seek(0)
    df = pd.read_csv(
        uploaded_file,
        sep=None,              # détecte , ou ;
        engine="python",
        encoding="utf-8-sig"   # gère le BOM ï»¿
    )
except Exception as e:
    st.error(f"Erreur de lecture du CSV : {e}")
    st.stop()

# =====================================================
# NETTOYAGE DES NOMS DE COLONNES (BOM / espaces)
# =====================================================
df.columns = (
    df.columns
    .str.replace("\ufeff", "", regex=False)
    .str.replace("ï»¿", "", regex=False)
    .str.strip()
)

# =====================================================
# VÉRIFICATION STRICTE DES COLONNES
# =====================================================
colonnes_attendues = ["Date", "Horaires", "Noms_dispos"]

if list(df.columns) != colonnes_attendues:
    st.error(
        "Le CSV doit contenir EXACTEMENT les colonnes : "
        + ", ".join(colonnes_attendues)
        + f"\nColonnes détectées : {df.columns.tolist()}"
    )
    st.stop()

# =====================================================
# APERÇU
# =====================================================
st.success("CSV importé correctement ✅")
st.dataframe(df)
