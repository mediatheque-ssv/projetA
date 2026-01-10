import streamlit as st
import pandas as pd
import random

# =====================================================
# CONFIG & TITRE
# =====================================================
st.set_page_config(
    page_title="Répartition mini-bénévoles",
    layout="wide"
)

st.markdown("""
<style>
/* Bouton principal */
.stButton>button {
    background-color: #6D28D9;
    color: white;
    border-radius: 14px;
    padding: 0.6em 1.2em;
    font-size: 1.05em;
    font-weight: 600;
}

/* Bouton au survol */
.stButton>button:hover {
    background-color: #5B21B6;
}

/* Cartes */
.card {
    border:1px solid #DDD6FE;
    border-radius:16px;
    padding:1em;
    margin-bottom:1em;
    background:#FAF5FF;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style="text-align:center;color:#6D28D9;">
🧩 Répartition mini-bénévoles
</h1>
""", unsafe_allow_html=True)

st.caption("Outil d’aide à la planification équitable")

st.divider()

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
st.markdown("## 📂 Import du CSV")
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if uploaded_file:

    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
    except Exception as e:
        st.error(f"Erreur de lecture du CSV : {e}")
        st.stop()

    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    if not {"Date", "Horaires", "Noms_dispos"}.issubset(df.columns):
        st.error("Colonnes requises : Date, Horaires, Noms_dispos")
        st.stop()

    st.markdown("### Aperçu du CSV")
    st.dataframe(df, use_container_width=True)

    # =====================================================
    # 2️⃣ EXTRACTION DES NOMS
    # =====================================================
    sample_cell = str(df["Noms_dispos"].iloc[0]) if len(df) > 0 else ""
    separator = "," if "," in sample_cell else ";"

    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        if pd.notna(cell)
        for n in str(cell).split(separator)
        if n.strip()
    })

    st.divider()
    st.markdown("## 🧒 Enfants et binômes détectés")

    df_noms = pd.DataFrame({
        "Enfant / binôme": noms_uniques,
        "Type": ["Binôme" if "/" in n else "Enfant seul" for n in noms_uniques]
    })

    st.dataframe(df_noms, use_container_width=True, hide_index=True)

    st.info(
        f"🔎 {len(noms_uniques)} entité(s) détectée(s) • "
        f"Séparateur : '{separator}' • "
        "Binôme = Nom1/Nom2"
    )

    # =====================================================
    # 3️⃣ PARAMÈTRES
    # =====================================================
    st.divider()
    st.markdown("## ⚙️ Paramètres des créneaux")

    col1, col2 = st.columns(2)
    with col1:
        min_par_date = st.slider("👥 Minimum par créneau", 1, 10, 4)
    with col2:
        max_par_date = st.slider("👥 Maximum par créneau", min_par_date, 10, max(5, min_par_date))

    # =====================================================
    # 4️⃣ DISPONIBILITÉS
    # =====================================================
    def compter_personnes(nom):
        return len(nom.split("/"))

    dispos_par_entite = {n: 0 for n in noms_uniques}
    for _, row in df.iterrows():
        for n in str(row["Noms_dispos"]).split(separator):
            n = n.strip()
            if n in dispos_par_entite:
                dispos_par_entite[n] += 1

    st.divider()
    st.markdown("## 📊 Disponibilités")

    df_dispos = (
        pd.DataFrame(dispos_par_entite.items(), columns=["Enfant / binôme", "Disponibilités"])
        .sort_values("Disponibilités")
        .reset_index(drop=True)
    )

    def style_dispos(v):
        if v <= 2:
            return "background-color:#FEE2E2"
        elif v <= 4:
            return "background-color:#FEF9C3"
        return ""

    st.dataframe(
        df_dispos.style.applymap(style_dispos, subset=["Disponibilités"]),
        use_container_width=True,
        hide_index=True
    )

    st.caption("🟥 Peu disponible • 🟨 Moyen • 🟩 Confortable")

    # =====================================================
    # 5️⃣ RÉPARTITION
    # =====================================================
    st.divider()
    st.markdown("## ▶️ Lancer la répartition")

    if st.button("✨ Répartir les enfants", use_container_width=True):

        compteur = {n: 0 for n in noms_uniques}
        affectations = {n: [] for n in noms_uniques}
        DELAI_MINIMUM = 6

        mois_fr = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }

        def parse_dt(row):
            try:
                parts = row["Date"].lower().split()
                jour = int(parts[1])
                mois = mois_fr.get(parts[2], 1)
                heure = int(row["Horaires"].split("h")[0])
                return pd.Timestamp(2026, mois, jour, heure)
            except:
                return pd.Timestamp("1900-01-01")

        df_sorted = df.copy()
        df_sorted["dt"] = df_sorted.apply(parse_dt, axis=1)
        df_sorted = df_sorted.sort_values("dt")

        creneaux_info = []
        for _, row in df_sorted.iterrows():
            dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator) if n.strip()]
            creneaux_info.append({
                "cle": f"{row['Date']} | {row['Horaires']}",
                "dt": row["dt"],
                "dispos": dispos,
                "affectes": []
            })

        for c in creneaux_info:
            candidats = []
            for n in c["dispos"]:
                if n in compteur:
                    candidats.append((
                        n,
                        compteur[n] + random.uniform(-0.5, 0.5),
                        dispos_par_entite[n] + random.uniform(-1, 1)
                    ))
            candidats.sort(key=lambda x: (x[1], x[2]))

            nb = 0
            for nom, _, _ in candidats:
                p = compter_personnes(nom)
                if nb + p <= max_par_date:
                    c["affectes"].append(nom)
                    compteur[nom] += 1
                    nb += p

        # =====================================================
        # 6️⃣ AFFICHAGE FINAL
        # =====================================================
        st.divider()
        st.markdown("## 🧩 Répartition finale")

        for c in creneaux_info:
            enfants = []
            for e in c["affectes"]:
                enfants.extend(e.split("/") if "/" in e else [e])

            st.markdown(f"""
            <div class="card">
            <strong>📅 {c['cle']}</strong><br>
            👧🧒 {", ".join(enfants) if enfants else "Aucun"}<br>
            ➕ {max_par_date - len(enfants)} place(s) restante(s)
            </div>
            """, unsafe_allow_html=True)

        # =====================================================
        # 7️⃣ OCCURRENCES
        # =====================================================
        st.divider()
        st.markdown("## 🔁 Occurrences")

        df_occ = (
            pd.DataFrame(compteur.items(), columns=["Enfant / binôme", "Occurrences"])
            .sort_values("Occurrences")
            .reset_index(drop=True)
        )

        max_occ = df_occ["Occurrences"].max()

        def style_occ(v):
            if v == 0:
                return "background-color:#FEE2E2"
            elif v == max_occ:
                return "background-color:#DDD6FE"
            return ""

        st.dataframe(
            df_occ.style.applymap(style_occ, subset=["Occurrences"]),
            use_container_width=True,
            hide_index=True
        )

        # =====================================================
        # 8️⃣ EXPORT
        # =====================================================
        export_df = pd.DataFrame([
            {
                "Date_Horaire": c["cle"],
                "Enfants_affectés": separator.join(c["affectes"]),
                "Places_restantes": max_par_date - sum(compter_personnes(n) for n in c["affectes"])
            }
            for c in creneaux_info
        ])

        csv = export_df.to_csv(index=False, sep=";").encode("utf-8")

        st.download_button(
            "⬇️ Télécharger la répartition CSV",
            data=csv,
            file_name="repartition.csv",
            mime="text/csv",
            use_container_width=True
        )
