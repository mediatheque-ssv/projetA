import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants")

uploaded_file = st.file_uploader("Importer le CSV", type=["csv"])
if not uploaded_file:
    st.stop()

# =====================================================
# 1️⃣ LECTURE SANS EN-TÊTE (ON S'EN FOUT D'EXCEL)
# =====================================================
uploaded_file.seek(0)
df_raw = pd.read_csv(
    uploaded_file,
    header=None,
    encoding="utf-8-sig"
)

# =====================================================
# 2️⃣ SI TOUT EST DANS UNE SEULE COLONNE → ON SPLIT
# =====================================================
if df_raw.shape[1] == 1:
    df = df_raw[0].astype(str).str.split(",", expand=True)
else:
    df = df_raw.copy()

# =====================================================
# 3️⃣ SUPPRESSION DE LA LIGNE D'EN-TÊTE EXCEL
# =====================================================
# On enlève la première ligne (Date,Horaires,Noms_dispos)
df = df.iloc[1:].reset_index(drop=True)

# =====================================================
# 4️⃣ ON FORCE LES BONS NOMS DE COLONNES
# =====================================================
df.columns = ["Date", "Horaires", "Noms_dispos"]

# =====================================================
# 5️⃣ APERÇU
# =====================================================
st.success("CSV importé correctement ✅")
st.dataframe(df)
