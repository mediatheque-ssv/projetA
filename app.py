import streamlit as st
import pandas as pd

st.title("Répartition bénévoles enfants")

# -----------------------------
# 1️⃣ Importer le fichier CSV
# -----------------------------
uploaded_file = st.file_uploader("Importer le CSV des disponibilités", type=["csv"])
if uploaded_file:
    try:
        # Essai avec UTF-8
        df = pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        # Si échec, utiliser un encodage plus tolérant
        df = pd.read_csv(uploaded_file, encoding='latin1')
    
    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    # -----------------------------
    # 2️⃣ Paramètre simple
    # -----------------------------
    max_par_creneau = st.slider("Nombre max d'enfants par créneau", 1, 10, 3)

    # -----------------------------
    # 3️⃣ Répartition simplifiée
    # -----------------------------
    st.write("Répartition simplifiée (exemple aléatoire)")
    
    creneaux = ["Mercredi matin", "Mercredi aprem", "Samedi matin"]
    repartition = {c: [] for c in creneaux}

    for index, row in df.iterrows():
        dispo = str(row["Créneaux possibles"]).split(";")  # convertit en string si vide
        for c in dispo:
            c = c.strip()  # enlever les espaces
            if c in repartition and len(repartition[c]) < max_par_creneau:
                repartition[c].append(row["Nom"])
                break  # on met l'enfant dans le premier créneau dispo

    # -----------------------------
    # 4️⃣ Affichage du résultat
    # -----------------------------
    for c, enfants in repartition.items():
        st.write(f"**{c}**: {', '.join(enfants) if enfants else 'Aucun enfant'}")

    # -----------------------------
    # 5️⃣ Option export CSV
    # -----------------------------
    export_df = pd.DataFrame([
        {"Créneau": c, "Enfants": ", ".join(enfants)} for c, enfants in repartition.items()
    ])
    csv = export_df.to_csv(index=False).encode('utf-8')
    st.download_button("Télécharger la répartition CSV", data=csv, file_name='repartition.csv', mime='text/csv')
