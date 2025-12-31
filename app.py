import streamlit as st
import pandas as pd

st.title("Répartition bénévoles / enfants par date")

uploaded_file = st.file_uploader(
    "Importer le CSV (Date / Noms_dispos)",
    type=["csv"]
)

if uploaded_file:
    # -----------------------------
    # Lecture CSV ultra robuste
    # -----------------------------
    try:
        df = pd.read_csv(
            uploaded_file,
            encoding="utf-8-sig",
            sep=None,          # ← détection automatique
            engine="python"
        )
    except Exception:
        df = pd.read_csv(
            uploaded_file,
            encoding="latin1",
            sep=";"
        )

    # Nettoyage des noms de colonnes
    df.columns = [c.replace("\ufeff", "").strip().lower() for c in df.columns]

    st.subheader("Colonnes détectées")
    st.write(df.columns.tolist())

    # Vérification des colonnes
    if "date" not in df.columns or "noms_dispos" not in df.columns:
        st.error(
            "Le CSV doit contenir les colonnes 'Date' et 'Noms_dispos'.\n\n"
            f"Colonnes détectées : {df.columns.tolist()}"
        )
        st.stop()

    st.subheader("Aperçu des données importées")
    st.dataframe(df)

    # -----------------------------
    # Paramètres
    # -----------------------------
    max_par_date = st.slider(
        "Nombre maximum d'enfants par date",
        1, 10, 3
    )

    # -----------------------------
    # Répartition
    # -----------------------------
    repartition = {}
    deja_affectes = set()
    non_affectes = set()

    for _, row in df.iterrows():
        date = str(row["date"]).strip()
        noms = str(row["noms_dispos"])

        repartition.setdefault(date, [])

        for nom in [n.strip() for n in noms.split(";") if n.strip()]:
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
        st.write(
            f"**{date}** : "
            f"{', '.join(enfants) if enfants else 'Aucun'} "
            f"({max_par_date - len(enfants)} place(s) restante(s))"
        )

    if non_affectes:
        st.warning(
            "Non affectés : " + ", ".join(sorted(non_affectes))
        )

    # -----------------------------
    # Export CSV
    # -----------------------------
    export_df = pd.DataFrame([
        {
            "Date": date,
            "Enfants_affectés": ";".join(enfants),
            "Places_restantes": max_par_date - len(enfants)
        }
        for date, enfants in repartition.items()
    ])

    csv = export_df.to_csv(index=False, sep=";").encode("utf-8")

    st.download_button(
        "Télécharger la répartition CSV",
        data=csv,
        file_name="repartition.csv",
        mime="text/csv"
    )
