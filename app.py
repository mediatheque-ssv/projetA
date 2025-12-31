import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants")

# Upload du fichier CSV
uploaded_file = st.file_uploader(
    "Importer le CSV des disponibilités",
    type=["csv"]
)

if uploaded_file:
    # Lecture du CSV avec gestion d'encodage
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding="latin1")

    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    # Curseur pour la capacité max par créneau
    max_par_creneau = st.slider(
        "Nombre maximum d'enfants par créneau",
        min_value=1,
        max_value=10,
        value=3
    )

    # -----------------------------
    # Extraction des créneaux depuis le CSV
    # -----------------------------
    creneaux = []
    for dispo in df["Dispo"].dropna():
        for c in str(dispo).split(";"):
            c = c.strip()
            if c and c not in creneaux:
                creneaux.append(c)

    # Initialisation de la répartition
    repartition = {c: [] for c in creneaux}

    # -----------------------------
    # Répartition des enfants
    # -----------------------------
    non_affectes = []

    for _, row in df.iterrows():
        nom = row["Nom"]
        dispos = str(row["Dispo"]).split(";")
        affecte = False

        for c in dispos:
            c = c.strip()
            if c in repartition and len(repartition[c]) < max_par_creneau:
                repartition[c].append(nom)
                affecte = True
                break

        if not affecte:
            non_affectes.append(nom)

    # -----------------------------
    # Affichage des résultats
    # -----------------------------
    st.subheader("Répartition finale")

    for c, enfants in repartition.items():
        places_restantes = max_par_creneau - len(enfants)
        st.write(
            f"**{c}** : "
            f"{', '.join(enfants) if enfants else 'Aucun enfant'} "
            f"(_{places_restantes} place(s) restante(s)_)"
        )

    if non_affectes:
        st.warning(
            "Non affectés : " + ", ".join(non_affectes)
        )

    # -----------------------------
    # Export CSV
    # -----------------------------
    export_df = pd.DataFrame(
        [
            {
                "Date": c,
                "Enfants": ", ".join(enfants),
                "Places restantes": max_par_creneau - len(enfants),
            }
            for c, enfants in repartition.items()
        ]
    )

    csv = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Télécharger la répartition CSV",
        data=csv,
        file_name="repartition.csv",
        mime="text/csv"
    )
