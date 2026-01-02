import streamlit as st
import pandas as pd
import random
from datetime import timedelta

st.title("Répartition améliorée bénévoles / enfants")

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if not uploaded_file:
    st.stop()

try:
    df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
except Exception as e:
    st.error(f"Erreur de lecture du CSV : {e}")
    st.stop()

df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

if not set(["Date", "Horaires", "Noms_dispos"]).issubset(set(df.columns)):
    st.error(
        "Le CSV doit contenir EXACTEMENT les colonnes : Date, Horaires, Noms_dispos\n"
        f"Colonnes détectées : {df.columns.tolist()}"
    )
    st.stop()

st.subheader("Aperçu du CSV")
st.dataframe(df)

# =====================================================
# 2️⃣ EXTRACTION DES NOMS
# =====================================================
noms_uniques = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    for n in str(cell).split(";")
    if n.strip()
})

st.subheader("Enfants détectés")
if noms_uniques:
    st.write(noms_uniques)
else:
    st.warning("Aucun enfant détecté ! Vérifie le CSV et le séparateur ';'")

# =====================================================
# 3️⃣ PARAMÈTRES DES CRÉNEAUX
# =====================================================
if noms_uniques:
    st.subheader("Paramètres des créneaux")

    min_par_date = st.slider(
        "Nombre minimal d'enfants par créneau",
        min_value=1, max_value=10, value=4
    )

    max_par_date = st.slider(
        "Nombre maximal d'enfants par créneau",
        min_value=min_par_date, max_value=10, value=max(5, min_par_date)
    )

    total_creaneaux = len(df)
    places_totales = total_creaneaux * max_par_date
    occ_recommandee = round(places_totales / len(noms_uniques))
    st.info(f"Total créneaux : {total_creaneaux}, Places totales : {places_totales} → Occurrence idéale par enfant ≈ {occ_recommandee}")
    
    max_occ_global = st.number_input(
        "Nombre maximal d'occurrences par enfant (pour tous)",
        min_value=1,
        max_value=total_creaneaux,
        value=occ_recommandee
    )

# =====================================================
# 4️⃣ BINÔMES
# =====================================================
st.subheader("Binômes à ne pas séparer")
if "binomes" not in st.session_state:
    st.session_state.binomes = []

if noms_uniques:
    col1, col2 = st.columns(2)
    with col1:
        enfant_a = st.selectbox("Enfant A", noms_uniques, key="a")
    with col2:
        enfant_b = st.selectbox("Enfant B", noms_uniques, key="b")

    if (
        enfant_a != enfant_b
        and st.button("Ajouter le binôme")
        and (enfant_a, enfant_b) not in st.session_state.binomes
        and (enfant_b, enfant_a) not in st.session_state.binomes
    ):
        st.session_state.binomes.append((enfant_a, enfant_b))

if st.session_state.binomes:
    st.write("Binômes définis :")
    for a, b in st.session_state.binomes:
        st.write(f"- {a} + {b}")

binomes = st.session_state.binomes

# =====================================================
# 5️⃣ RÉPARTITION AMÉLIORÉE
# =====================================================
if st.button("Répartir les enfants"):

    # ---- Préparer les créneaux
    df["Date_dt"] = pd.to_datetime(df["Date"], dayfirst=True)
    df_sorted = df.sort_values("Date_dt").reset_index(drop=True)

    repartition = {}
    compteur = {nom: 0 for nom in noms_uniques}
    dernier_creneau = {nom: pd.Timestamp.min for nom in noms_uniques}

    for _, row in df_sorted.iterrows():
        date = pd.to_datetime(row["Date"], dayfirst=True)
        horaire = str(row["Horaires"]).strip()
        dispo = [n.strip() for n in str(row["Noms_dispos"]).split(";") if n.strip()]
        cle = f"{date.strftime('%d/%m/%Y')} | {horaire}"
        repartition[cle] = []

        deja_affectes = set()

        # ---- Ajouter binômes disponibles
        binomes_dispos = []
        for a, b in binomes:
            if (a in dispo and b in dispo
                and compteur[a] < max_occ_global
                and compteur[b] < max_occ_global
                and len(repartition[cle]) <= max_par_date - 2
                and (date - dernier_creneau[a]).days >= 14
                and (date - dernier_creneau[b]).days >= 14
            ):
                binomes_dispos.append((a, b))
        random.shuffle(binomes_dispos)
        for a, b in binomes_dispos:
            repartition[cle].extend([a, b])
            compteur[a] += 1
            compteur[b] += 1
            dernier_creneau[a] = date
            dernier_creneau[b] = date
            deja_affectes.update([a, b])

        # ---- Ajouter solos disponibles
        solos_dispos = [
            n for n in dispo
            if n not in deja_affectes
            and compteur[n] < max_occ_global
            and (date - dernier_creneau[n]).days >= 14
        ]
        solos_dispos.sort(key=lambda x: compteur[x])
        for n in solos_dispos:
            if len(repartition[cle]) < max_par_date:
                repartition[cle].append(n)
                compteur[n] += 1
                dernier_creneau[n] = date
                deja_affectes.add(n)

        # ---- Vérifier min_par_date
        if len(repartition[cle]) < min_par_date:
            restants = [
                n for n in noms_uniques
                if n not in deja_affectes and compteur[n] < max_occ_global
            ]
            random.shuffle(restants)
            for n in restants:
                if len(repartition[cle]) < min_par_date:
                    repartition[cle].append(n)
                    compteur[n] += 1
                    dernier_creneau[n] = date
                    deja_affectes.add(n)
                else:
                    break

    # ---- Tri final
    def cle_tri(cle_str):
        date_str, horaire_str = cle_str.split("|")
        try:
            return (pd.to_datetime(date_str.strip(), dayfirst=True), horaire_str.strip())
        except:
            return (date_str.strip(), horaire_str.strip())

    repartition_tri = dict(sorted(repartition.items(), key=cle_tri))

    # =====================================================
    # 6️⃣ AFFICHAGE
    # =====================================================
    st.subheader("Répartition finale (triée par date)")
    for cle, enfants in repartition_tri.items():
        st.write(
            f"{cle} : "
            f"{', '.join(enfants) if enfants else 'Aucun'} "
            f"({max_par_date - len(enfants)} place(s) restante(s))"
        )

    st.subheader("Occurrences par enfant")
    st.write(dict(sorted(compteur.items())))

    jamais_affectes = [nom for nom, c in compteur.items() if c == 0]
    if jamais_affectes:
        st.subheader("Enfants jamais affectés")
        st.write(", ".join(jamais_affectes))

    # =====================================================
    # 7️⃣ EXPORT CSV
    # =====================================================
    export_df = pd.DataFrame([
        {
            "Date_Horaire": cle,
            "Enfants_affectés": ";".join(enfants),
            "Places_restantes": max_par_date - len(enfants)
        }
        for cle, enfants in repartition_tri.items()
    ])
    csv = export_df.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        "Télécharger la répartition CSV",
        data=csv,
        file_name="repartition.csv",
        mime="text/csv"
    )
