import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants par date")

# Upload du CSV
uploaded_file = st.file_uploader(
    "Importer le CSV (Excel FR – séparateur ;)",
    type=["csv"]
)

if uploaded_file:
    # -----------------------------
    # Lecture du CSV (Excel FR)
    # -----------------------------
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8", sep=";")
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding="latin1", sep=";")

    # Nettoyage des noms de colonnes
    df.columns = df.columns.str.strip()

    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    # Vérification des colonnes attendues
    colonnes_attendues = {"Date", "Noms_dispos"}
    if not colonnes_attendues.issubset(df.columns):
        st.error(
            f"Colonnes détectées : {', '.join(df.columns)}\n\n"
            "Colonnes attendues : Date ; Noms_dispos"
        )
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
        noms_cellule = str(row["Noms_dispos"])

        repartition[date] = []

        # Séparation des noms
        noms = [n.strip() for n in noms_cellule.split(";") if n.strip()]

        for nom in noms:
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
    # Export CSV (Excel FR)
    # -----------------------------
    export_df = pd.DataFrame(
        [
            {
                "Date": date,
                "Enfants_affectés": ";".join(enfants),
                "Places_restantes": max_par_date - len(enfants),
            }
            for date, enfants in repartition.items()
        ]
    )

    csv = export_df.to_csv(index=False, sep=";").encode("utf-8")

    st.download_button(
        "Télécharger la répartition CSV",
        data=csv,
        file_name="repartition.csv",
        mime="text/csv"
    )
