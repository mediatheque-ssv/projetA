import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants par date")

uploaded_file = st.file_uploader(
    "Importer le CSV (Excel FR – séparateur ;)",
    type=["csv"]
)

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8-sig", sep=";")
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding="latin1", sep=";")

    # Normalisation colonnes
    df.columns = [c.replace("\ufeff", "").strip().lower() for c in df.columns]

    st.subheader("Colonnes détectées")
    st.write(df.columns.tolist())

    colonnes_attendues = ["date", "noms_dispos"]

    if not all(c in df.columns for c in colonnes_attendues):
        st.error(
            f"Colonnes détectées : {df.columns.tolist()}\n"
            f"Colonnes attendues : {colonnes_attendues}"
        )
        st.stop()

    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    max_par_date = st.slider(
        "Nombre maximum d'enfants par date",
        min_value=1,
        max_value=10,
        value=3
    )

    repartition = {}
    deja_affectes = set()
    non_affectes = set()

    for _, row in df.iterrows():
        date = str(row["date"]).strip()
        noms_cellule = str(row["noms_dispos"])

        if date not in repartition:
            repartition[date] = []

        noms = [n.strip() for n in noms_cellule.split(";") if n.strip()]

        for nom in noms:
            if nom not in deja_affectes and len(repartition[date]) < max_par_date:
                repartition[date].append(nom)
                deja_affectes.add(nom)
            else:
                non_affectes.add(nom)

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
            "Non affectés : " + ", ".join(sorted(non_affectes))
        )

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
