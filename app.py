import streamlit as st
import pandas as pd
import random

st.title("Répartition enfants – groupes inséparables")

# =====================================================
# 1️⃣ Import CSV
# =====================================================
uploaded_file = st.file_uploader(
    "Importer le CSV (Date ; Horaires ; Noms_dispos)",
    type=["csv"]
)

if not uploaded_file:
    st.stop()

df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

if not {"Date", "Horaires", "Noms_dispos"}.issubset(df.columns):
    st.error("Colonnes requises : Date ; Horaires ; Noms_dispos")
    st.stop()

# =====================================================
# 2️⃣ Enfants détectés
# =====================================================
sample = str(df["Noms_dispos"].iloc[0])
separator = "," if "," in sample else ";"

noms = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    if pd.notna(cell)
    for n in str(cell).split(separator)
    if n.strip()
})

# =====================================================
# 3️⃣ Paramètres globaux
# =====================================================
st.subheader("Paramètres globaux")
min_par_date = st.slider("Min enfants par créneau", 1, 10, 2)
max_par_date = st.slider("Max enfants par créneau", min_par_date, 10, 5)
delai_min = st.slider("Délai minimum entre deux présences (jours)", 0, 14, 7)

# =====================================================
# 4️⃣ Binômes
# =====================================================
st.subheader("Binômes inséparables")

if "binomes" not in st.session_state:
    st.session_state.binomes = []

a = st.selectbox("Enfant A", noms)
b = st.selectbox("Enfant B", noms)

if st.button("Ajouter le binôme"):
    if a != b:
        st.session_state.binomes.append((a, b))

for x, y in st.session_state.binomes:
    st.write(f"• {x} + {y}")

# =====================================================
# 5️⃣ Groupes
# =====================================================
groupes = []
utilises = set()

for a, b in st.session_state.binomes:
    groupes.append([a, b])
    utilises.update([a, b])

for n in noms:
    if n not in utilises:
        groupes.append([n])

# =====================================================
# 6️⃣ Dates
# =====================================================
mois = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3
}

def parse_dt(row):
    try:
        d = str(row["Date"]).lower().split()
        h = str(row["Horaires"])
        return pd.Timestamp(
            year=2026,
            month=mois[d[2]],
            day=int(d[1]),
            hour=int(h.split("h")[0])
        )
    except:
        return pd.Timestamp("1900-01-01")

df["dt"] = df.apply(parse_dt, axis=1)
df = df.sort_values("dt")

creneaux = []
for _, r in df.iterrows():
    if r["dt"] == pd.Timestamp("1900-01-01"):
        continue
    creneaux.append({
        "cle": f"{r['Date']} | {r['Horaires']}",
        "dt": r["dt"],
        "dispos": [n.strip() for n in str(r["Noms_dispos"]).split(separator)],
        "affectes": []
    })

# =====================================================
# 7️⃣ Dispos max par groupe
# =====================================================
def groupe_dispo(g, dispo):
    return all(m in dispo for m in g)

dispo_max = {
    tuple(g): sum(groupe_dispo(g, str(c).split(separator)) for c in df["Noms_dispos"])
    for g in groupes
}

# =====================================================
# 8️⃣ Min / Max par groupe
# =====================================================
st.subheader("Occurrences par groupe")

occ_min = {}
occ_max = {}

for g in groupes:
    key = tuple(g)
    label = " + ".join(g)
    col1, col2 = st.columns(2)

    with col1:
        occ_min[key] = st.number_input(
            f"{label} – MIN (max dispo {dispo_max[key]})",
            0,
            dispo_max[key],
            min(1, dispo_max[key])
        )
    with col2:
        occ_max[key] = st.number_input(
            f"{label} – MAX",
            occ_min[key],
            dispo_max[key],
            dispo_max[key]
        )

# =====================================================
# 9️⃣ Répartition
# =====================================================
if st.button("Lancer la répartition"):
    affectations = {n: [] for n in noms}
    compteur = {n: 0 for n in noms}

    # 🎯 Étape 1 : atteindre les MIN
    for g in groupes:
        key = tuple(g)
        restant = occ_min[key]

        for c in creneaux:
            if restant <= 0:
                break

            if len(c["affectes"]) + len(g) > max_par_date:
                continue
            if not groupe_dispo(g, c["dispos"]):
                continue
            if any(m in c["affectes"] for m in g):
                continue
            if any(compteur[m] >= occ_max[key] for m in g):
                continue

            if any(
                affectations[m]
                and (c["dt"] - affectations[m][-1]).days < delai_min
                for m in g
            ):
                continue

            for m in g:
                c["affectes"].append(m)
                compteur[m] += 1
                affectations[m].append(c["dt"])

            restant -= 1

    # 🔁 Étape 2 : compléter les créneaux
    for c in creneaux:
        while len(c["affectes"]) < min_par_date:
            candidats = [
                g for g in groupes
                if len(c["affectes"]) + len(g) <= max_par_date
                and groupe_dispo(g, c["dispos"])
                and not any(m in c["affectes"] for m in g)
                and not any(compteur[m] >= occ_max[tuple(g)] for m in g)
            ]

            if not candidats:
                break

            g = random.choice(candidats)
            for m in g:
                c["affectes"].append(m)
                compteur[m] += 1
                affectations[m].append(c["dt"])

    # =====================================================
    # 🔟 Résultat
    # =====================================================
    st.subheader("Répartition finale")
    for c in creneaux:
        st.write(
            f"{c['cle']} → "
            f"{', '.join(c['affectes']) if c['affectes'] else 'Aucun'} "
            f"({max_par_date - len(c['affectes'])} place(s))"
        )

    st.subheader("Compteur final")
    st.write(compteur)
