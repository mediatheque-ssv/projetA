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
    # Lecture du CSV avec Excel FR
    # -----------------------------
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8-sig", sep=";")
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding="latin1", sep=";")

    # 🔹 Normalisation forte des colonnes
    df.columns = (
        df.columns
        .str.replace("\ufeff", "", regex=False)  # enlève BOM
        .str.strip()
        .str.lower()
    )

    # 🔹 Mapping tolérant pour les noms de colonnes
    mapping_colonnes = {
        "date": "date",
        "jour": "date",
        "noms_dispos": "noms_dispos",
        "noms dispos": "noms_dispos",
        "dispos": "noms_dispos",
    }

    df = df.rename(columns={col: mapping_colonnes.get(col, col) for col in df.columns})

    # Vérification finale des colonnes
    if not {"date", "noms_dispos"}.issubset(df.columns):
        st.error(
            f"Colonnes détectées : {df.columns.tolist()}\n"
            "Colonnes attendues : date, noms_dispos"
        )
        st.stop()

    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    # -----------------------------
    # Capacité max par date
    # -----------------------------
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
        date = str(row["date"]).strip()
        noms_cellule = str(row["noms_dispos"])

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
    # Affichage des résultats
    # -----------------------------
    st.subheader("Répartition finale")

    for date, enfants in repartition.items():
        places_restantes = max_par_date - len(enfants)
        st.write(
            f"**{date}** : "
            f"{', '.join(enfants) if enfants else 'Aucun enfant'} "
            f"({places_restantes} place(s) restante(s))"
        )

    if non_affectes:
        st.warning(
            "Non affectés (déjà pris ou manque de place) : "
            + ", ".join(sorted(non_affectes))
        )

    # -----------------------------
    # Export CSV compatible Excel FR
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
