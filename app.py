import streamlit as st
import pandas as pd

st.title("Répartition bénévoles enfants")

uploaded_file = st.file_uploader("Importer le CSV des disponibilités", type=["csv"])
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding='latin1')

    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    max_par_creneau = st.slider("Nombre max d'enfants par créneau", 1, 10, 3)

    creneaux = ["05/12/2026", "07/12/2026", "09/12/2026"]
    repartition = {c: [] for c in creneaux}

    for index, row in df.iterrows():
        dispo = str(row["Dispo"]).split(";")
        for c in dispo:
            c = c.strip()
            if c in repartition and len(repartition[c]) < max_par_creneau:
                repartition[c].append(row["Nom"])
                break

    for c, enfants in repartition.items():
        st.write(f"**{c}**: {', '.join(enfants) if enfants else 'Aucun enfant'}")

    export_df = pd.DataFrame([
        {"Date": c, "Enfants": ", ".join(enfants)} for c, enfants in repartition.items()
    ])
    csv = export_df.to_csv(index=False).encode('utf-8')
    st.download_button("Télécharger la répartition CSV", data=csv, file_name='repartition.csv', mime='text/csv')
