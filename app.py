import streamlit as st
import pandas as pd

st.title("Répartition bénévoles enfants")

# Importer le CSV
uploaded_file = st.file_uploader("Importer le CSV des disponibilités", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file, encoding='utf-8')
    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    # Paramètre simple : nombre max par créneau
    max_par_creneau = st.slider("Nombre max d'enfants par créneau", 1, 10, 3)

    st.write("Répartition simplifiée (exemple aléatoire)")
    
    # Exemple de répartition simplifiée (juste afficher les enfants par créneau disponible)
    creneaux = ["Mercredi matin", "Mercredi aprem", "Samedi matin"]
    repartition = {c: [] for c in creneaux}

    for index, row in df.iterrows():
        dispo = row["Créneaux possibles"].split(";")
        for c in dispo:
            if len(repartition[c]) < max_par_creneau:
                repartition[c].append(row["Nom"])
                break  # on met l'enfant dans le premier créneau dispo

    # Affichage
    for c, enfants in repartition.items():
        st.write(f"**{c}**: {', '.join(enfants)}")

