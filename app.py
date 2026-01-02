import streamlit as st
import pandas as pd
import random

st.title("Répartition avec groupes (binômes inséparables)")

# =====================================================
# 1️⃣ Import CSV
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
if not {"Date", "Horaires", "Noms_dispos"}.issubset(df.columns):
    st.error("Colonnes requises : Date ; Horaires ; Noms_dispos")
    st.stop()

st.subheader("Aperçu du CSV")
st.dataframe(df.head(10))

# =====================================================
# 2️⃣ Extraction des enfants
# =====================================================
sample = str(df["Noms_dispos"].iloc[0])
separator = "," if "," in sample else ";"

noms_uniques = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    if pd.notna(cell)
    for n in str(cell).split(separator)
    if n.strip()
})

st.subheader("Enfants détectés")
st.write(noms_uniques)

# =====================================================
# 3️⃣ Paramètres globaux
# =====================================================
st.subheader("Paramètres")
min_par_date = st.slider("Nombre minimal d'enfants par créneau", 1, 10, 2)
max_par_date = st.slider("Nombre maximal d'enfants par créneau", min_par_date, 10, 5)
delai_minimum = st.slider("Délai minimum entre deux présences (jours)", 1, 14, 7)

# =====================================================
# 4️⃣ Gestion des binômes
# =====================================================
st.subheader("Binômes inséparables")

if "binomes" not in st.session_state:
    st.session_state.binomes = []

col1, col2 = st.columns(2)
with col1:
    enfant_a = st.selectbox("Enfant A", noms_uniques)
with col2:
    enfant_b = st.selectbox("Enfant B", noms_uniques)

if st.button("Ajouter le binôme"):
    if enfant_a != enfant_b:
        if (enfant_a, enfant_b) not in st.session_state.binomes and \
           (enfant_b, enfant_a) not in st.session_state.binomes:
            st.session_state.binomes.append((enfant_a, enfant_b))

if st.session_state.binomes:
    st.write("Binômes définis :")
    for a, b in st.session_state.binomes:
        st.write(f"- {a} + {b}")

# =====================================================
# 5️⃣ Construction des groupes
# =====================================================
groupes = []
utilises = set()

for a, b in st.session_state.binomes:
    groupes.append([a, b])
    utilises.add(a)
    utilises.add(b)

for nom in noms_uniques:
    if nom not in utilises:
        groupes.append([nom])

# =====================================================
# 6️⃣ Parsing des dates
# =====================================================
mois_fr = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3
}

def parse_dt(row):
    try:
        d = str(row["Date"]).lower().split()
        h = str(row["Horaires"])
        jour = int(d[1])
        mois = mois_fr[d[2]]
        heure = int(h.split("h")[0]) if "h" in h else 0
        return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure)
    except:
        return pd.Timestamp("1900-01-01")

df["dt"] = df.apply(parse_dt, axis=1)
df = df.sort_values("dt")

creneaux = []
for _, row in df.iterrows():
    if row["dt"] == pd.Timestamp("1900-01-01"):
        continue
    dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator)]
    creneaux.append({
        "cle": f"{row['Date']} | {row['Horaires']}",
        "dt": row["dt"],
        "dispos": dispos,
        "affectes": []
    })

# =====================================================
# 7️⃣ Dispos max par groupe
# =====================================================
def groupe_dispo(groupe, dispo):
    return all(m in dispo for m in groupe)

dispo_max = {}
for g in groupes:
    dispo_max[tuple(g)] = sum(
        groupe_dispo(g, str(cell).split(separator))
        for cell in df["Noms_dispos"]
    )

# =====================================================
# 8️⃣ Occurrence minimale par groupe
# =====================================================
st.subheader("Occurrence minimale par groupe")

occur_min = {}
for g in groupes:
    label = " + ".join(g)
    occur_min[tuple(g)] = st.number_input(
        f"{label} (max dispo {dispo_max[tuple(g)]})",
        min_value=0,
        max_value=dispo_max[tuple(g)],
        value=min(1, dispo_max[tuple(g)])
    )

# =====================================================
# 9️⃣ Répartition
# =====================================================
if st.button("Lancer la répartition"):
    compteur = {n: 0 for n in noms_uniques}
    affectations = {n: [] for n in noms_uniques}

    # Étape 1 : atteindre l'occurrence minimale
    for g in groupes:
        g_key = tuple(g)
        restant = occur_min[g_key]

        for c in creneaux:
            if restant <= 0:
                break

            if len(c["affectes"]) + len(g) > max_par_date:
                continue

            if not groupe_dispo(g, c["dispos"]):
                continue

            if any(m in c["affectes"] for m in g):
                continue

            ok_delai = True
            for m in g:
                last = affectations[m][-1] if affectations[m] else pd.Timestamp("1900-01-01")
                if (c["dt"] - last).days < delai_minimum:
                    ok_delai = False
                    break

            if not ok_delai:
                continue

            for m in g:
                c["affectes"].append(m)
                compteur[m] += 1
                affectations[m].append(c["dt"])

            restant -= 1

    # Étape 2 : atteindre le minimum par créneau
    for c in creneaux:
        while len(c["affectes"]) < min_par_date:
            candidats = [
                g for g in groupes
                if len(c["affectes"]) + len(g) <= max_par_date
                and groupe_dispo(g, c["dispos"])
                and not any(m in c["affectes"] for m in g)
            ]
            if not candidats:
                break

            g = random.choice(candidats)
            for m in g:
                c["affectes"].append(m)
                compteur[m] += 1
                affectations[m].append(c["dt"])

    # =====================================================
    # 🔟 Affichage
    # =====================================================
    st.subheader("Répartition finale")
    for c in creneaux:
        st.write(
            f"{c['cle']} → "
            f"{', '.join(c['affectes']) if c['affectes'] else 'Aucun'} "
            f"({max_par_date - len(c['affectes'])} place(s))"
        )

    st.subheader("Nombre de créneaux par enfant")
    st.write(compteur)
