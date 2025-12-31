import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants par date")

# Upload du CSV
uploaded_file = st.file_uploader(
    "Importer le CSV (Date / Noms_dispos)",
    type=["csv"]
)

if uploaded_file:
    # Lecture du CSV avec gestion d'encodage
    try:
    df = pd.read_csv(uploaded_file, encoding="utf-8", sep=";")
    except UnicodeDecodeError:
    df = pd.read_csv(uploaded_file, encoding="latin1", sep=";")


    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    # Vérification minimale
    if not {"Date", "Noms_dispos"}.issubset(df.columns):
        st.error("Le CSV doit contenir les colonnes 'Date' et 'Noms_dispos'")
        st.stop()

    # Capacité max par date
    max_par_date = st.slider(
        "Nombre maximum d'enfants par date",
        min_value=1,
        max_value=10,
        value=3
    )

    # -----------------------------
    # Répartition
    # -----------------------------
    repartition = {}
    deja_affectes = set()
    non_affectes = set()

    for _, row in df.iterrows():
        date = str(row["Date"]).strip()
        noms = str(row["Noms_dispos"]).split(";")

        repartition[date] = []

        for nom in noms:
            nom = nom.strip()
            if not nom:
                continue

            if nom not in deja_affectes and len(repartition[date]) < max_par_date:
                repartition[date].append(nom)
                deja_affectes.add(nom)
            else:
                non_affectes.add(nom)

    # -----------------------------
    # Affichage
    # -----------------------------
    st.subheader("Répartition finale")

    for date, enfants in repartition.items():
        places_restantes = max_par_date - len(enfants)
        st.write(
            f"**{date}** : "
            f"{', '.join(enfants) if enfants else 'Aucun enfant'} "
            f"(_{places_restantes} place(s) restante(s)_)"
        )

    if non_affectes:
        st.warning(
            "Non affectés (déjà pris ou manque de place) : "
            + ", ".join(sorted(non_affectes))
        )

    # -----------------------------
    # Export CSV
    # -----------------------------
    export_df = pd.DataFrame(
        [
            {
                "Date": date,
                "Enfants_affectés": ", ".join(enfants),
                "Places_restantes": max_par_date - len(enfants),
            }
            for date, enfants in repartition.items()
        ]
    )

    csv = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Télécharger la répartition CSV",
        data=csv,
        file_name="repartition.csv",
        mime="text/csv"
    )

