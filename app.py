import streamlit as st
import pandas as pd
from datetime import timedelta

st.set_page_config(layout="wide")
st.title("Répartition humaine des enfants (logique progressive)")

# =====================================================
# 1️⃣ IMPORT CSV
# =====================================================
uploaded_file = st.file_uploader("Importer le CSV (Date ; Horaires ; Noms_dispos)", type=["csv"])

if not uploaded_file:
    st.stop()

df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig")
df.columns = [c.strip() for c in df.columns]

# =====================================================
# 2️⃣ PARAMÈTRES SIMPLES
# =====================================================
st.subheader("Paramètres globaux")

col1, col2, col3 = st.columns(3)
with col1:
    min_par_creneau = st.number_input("Min enfants par créneau", 1, 10, 4)
    max_par_creneau = st.number_input("Max enfants par créneau", min_par_creneau, 10, 5)
with col2:
    delai_min = st.number_input("Délai minimum entre 2 présences (jours)", 1, 21, 7)
with col3:
    min_occ = st.number_input("Occurrence minimale par enfant", 0, 10, 2)
    max_occ = st.number_input("Occurrence maximale par enfant", min_occ, 20, 6)

# =====================================================
# 3️⃣ BINÔMES
# =====================================================
st.subheader("Binômes inséparables")

all_names = sorted(set(
    n.strip()
    for cell in df["Noms_dispos"]
    for n in str(cell).replace(",", ";").split(";")
))

if "binomes" not in st.session_state:
    st.session_state.binomes = []

c1, c2 = st.columns(2)
with c1:
    a = st.selectbox("Enfant A", all_names)
with c2:
    b = st.selectbox("Enfant B", all_names)

if st.button("Ajouter binôme") and a != b:
    if (a, b) not in st.session_state.binomes and (b, a) not in st.session_state.binomes:
        st.session_state.binomes.append((a, b))

st.write(st.session_state.binomes)

# =====================================================
# 4️⃣ DATES
# =====================================================
mois_fr = {
    "janvier": 1, "février": 2, "fevrier": 2,
    "mars": 3, "avril": 4
}

def parse_dt(row):
    parts = str(row["Date"]).lower().split()
    jour = int(parts[1])
    mois = mois_fr[parts[2]]
    heure = int(str(row["Horaires"]).split("h")[0])
    return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure)

df["dt"] = df.apply(parse_dt, axis=1)
df = df.sort_values("dt")

# =====================================================
# 5️⃣ CRÉNEAUX
# =====================================================
creneaux = []
for _, row in df.iterrows():
    dispos = [n.strip() for n in str(row["Noms_dispos"]).replace(",", ";").split(";")]
    creneaux.append({
        "cle": f"{row['Date']} | {row['Horaires']}",
        "dt": row["dt"],
        "dispos": dispos,
        "affectes": []
    })

# =====================================================
# 6️⃣ BLOCS (binômes fusionnés)
# =====================================================
bloc_map = {}
used = set()

for a, b in st.session_state.binomes:
    bloc_map[a] = f"{a}+{b}"
    bloc_map[b] = f"{a}+{b}"
    used.update([a, b])

for n in all_names:
    if n not in used:
        bloc_map[n] = n

blocs = sorted(set(bloc_map.values()))

# =====================================================
# 7️⃣ DISPONIBILITÉS PAR BLOC
# =====================================================
bloc_dispos = {b: [] for b in blocs}
for i, c in enumerate(creneaux):
    for n in c["dispos"]:
        bloc = bloc_map.get(n)
        if bloc:
            bloc_dispos[bloc].append(i)

# =====================================================
# 8️⃣ ÉTAT
# =====================================================
occ = {b: 0 for b in blocs}
last_date = {b: None for b in blocs}

# =====================================================
# 9️⃣ TRI PAR URGENCE
# =====================================================
def urgence(bloc):
    dispos = len(bloc_dispos[bloc])
    if dispos == 0:
        return 999
    return (min_occ - occ[bloc]) / dispos

# =====================================================
# 🔟 PLACEMENT POUR ATTEINDRE LE MIN
# =====================================================
for bloc in sorted(blocs, key=urgence):
    while occ[bloc] < min_occ:
        placed = False
        for i in bloc_dispos[bloc]:
            c = creneaux[i]
            if occ[bloc] >= min_occ:
                break
            if len(c["affectes"]) >= max_par_creneau:
                continue
            if bloc in c["affectes"]:
                continue
            if last_date[bloc]:
                if (c["dt"] - last_date[bloc]).days < delai_min:
                    continue
            c["affectes"].append(bloc)
            occ[bloc] += 1
            last_date[bloc] = c["dt"]
            placed = True
        if not placed:
            break

# =====================================================
# 1️⃣1️⃣ REMPLISSAGE VERS LE MAX
# =====================================================
for c in creneaux:
    while len(c["affectes"]) < min_par_creneau:
        candidats = sorted(
            [b for b in blocs if b in bloc_dispos and creneaux.index(c) in bloc_dispos[b] and occ[b] < max_occ],
            key=lambda b: occ[b]
        )
        if not candidats:
            break
        b = candidats[0]
        c["affectes"].append(b)
        occ[b] += 1
        last_date[b] = c["dt"]

# =====================================================
# 1️⃣2️⃣ AFFICHAGE
# =====================================================
st.subheader("Planning final")

for c in creneaux:
    noms = []
    for b in c["affectes"]:
        noms.extend(b.split("+"))
    st.write(f"{c['cle']} → {', '.join(noms)} ({max_par_creneau - len(c['affectes'])} place(s))")

# =====================================================
# 1️⃣3️⃣ STATS
# =====================================================
st.subheader("Occurrences")
for b in blocs:
    st.write(f"{b} : {occ[b]}")
