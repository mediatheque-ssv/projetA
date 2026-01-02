import streamlit as st
import pandas as pd
from datetime import timedelta

st.set_page_config(layout="wide")
st.title("Répartition humaine corrigée (anti-doublons & anti-copier-coller)")

# =====================================================
# 1️⃣ IMPORT CSV
# =====================================================
uploaded_file = st.file_uploader("Importer le CSV (Date ; Horaires ; Noms_dispos)", type=["csv"])
if not uploaded_file:
    st.stop()

df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig")
df.columns = [c.strip() for c in df.columns]

# =====================================================
# 2️⃣ PARAMÈTRES
# =====================================================
st.subheader("Paramètres")

c1, c2, c3 = st.columns(3)
with c1:
    min_par_creneau = st.number_input("Min par créneau", 1, 10, 4)
    max_par_creneau = st.number_input("Max par créneau", min_par_creneau, 10, 5)
with c2:
    delai_min = st.number_input("Délai minimum (jours)", 1, 21, 7)
with c3:
    min_occ = st.number_input("Occurrence min par enfant", 0, 10, 2)
    max_occ = st.number_input("Occurrence max par enfant", min_occ, 20, 6)

# =====================================================
# 3️⃣ BINÔMES
# =====================================================
all_names = sorted(set(
    n.strip()
    for cell in df["Noms_dispos"]
    for n in str(cell).replace(",", ";").split(";")
))

if "binomes" not in st.session_state:
    st.session_state.binomes = []

st.subheader("Binômes inséparables")

b1, b2 = st.columns(2)
with b1:
    a = st.selectbox("Enfant A", all_names)
with b2:
    b = st.selectbox("Enfant B", all_names)

if st.button("Ajouter binôme") and a != b:
    if (a, b) not in st.session_state.binomes and (b, a) not in st.session_state.binomes:
        st.session_state.binomes.append((a, b))

st.write(st.session_state.binomes)

# =====================================================
# 4️⃣ PARSE DATES
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
        "affectes": []   # blocs
    })

# =====================================================
# 6️⃣ BLOCS (binômes fusionnés)
# =====================================================
bloc_of = {}
bloc_size = {}

used = set()
for a, b in st.session_state.binomes:
    bloc = f"{a}+{b}"
    bloc_of[a] = bloc
    bloc_of[b] = bloc
    bloc_size[bloc] = 2
    used.update([a, b])

for n in all_names:
    if n not in used:
        bloc_of[n] = n
        bloc_size[n] = 1

blocs = sorted(set(bloc_of.values()))

# =====================================================
# 7️⃣ DISPONIBILITÉS PAR BLOC
# =====================================================
bloc_dispos = {b: [] for b in blocs}
for i, c in enumerate(creneaux):
    for n in c["dispos"]:
        bloc = bloc_of.get(n)
        if bloc and i not in bloc_dispos[bloc]:
            bloc_dispos[bloc].append(i)

# =====================================================
# 8️⃣ ÉTAT
# =====================================================
occ = {b: 0 for b in blocs}
last_date = {b: None for b in blocs}
groupes_utilises = set()   # anti copier-coller

# =====================================================
# 9️⃣ URGENCE
# =====================================================
def urgence(bloc):
    d = len(bloc_dispos[bloc])
    if d == 0:
        return 999
    return (min_occ - occ[bloc]) / d

# =====================================================
# 🔟 PHASE 1 : ATTEINDRE LES MIN
# =====================================================
for bloc in sorted(blocs, key=urgence):
    while occ[bloc] < min_occ:
        placed = False
        for i in bloc_dispos[bloc]:
            c = creneaux[i]

            taille = sum(bloc_size[b] for b in c["affectes"])
            if taille + bloc_size[bloc] > max_par_creneau:
                continue

            if bloc in c["affectes"]:
                continue

            if last_date[bloc] and (c["dt"] - last_date[bloc]).days < delai_min:
                continue

            futur_groupe = tuple(sorted(c["affectes"] + [bloc]))
            if futur_groupe in groupes_utilises:
                continue

            c["affectes"].append(bloc)
            occ[bloc] += 1
            last_date[bloc] = c["dt"]
            groupes_utilises.add(futur_groupe)
            placed = True
            break

        if not placed:
            break

# =====================================================
# 1️⃣1️⃣ PHASE 2 : REMPLISSAGE HUMAIN
# =====================================================
for c in creneaux:
    while sum(bloc_size[b] for b in c["affectes"]) < min_par_creneau:
        candidats = [
            b for b in blocs
            if creneaux.index(c) in bloc_dispos[b]
            and b not in c["affectes"]
            and occ[b] < max_occ
            and sum(bloc_size[x] for x in c["affectes"]) + bloc_size[b] <= max_par_creneau
        ]

        if not candidats:
            break

        candidats.sort(key=lambda b: occ[b])

        choisi = None
        for b in candidats:
            futur = tuple(sorted(c["affectes"] + [b]))
            if futur not in groupes_utilises:
                choisi = b
                break

        if not choisi:
            break

        c["affectes"].append(choisi)
        occ[choisi] += 1
        last_date[choisi] = c["dt"]
        groupes_utilises.add(tuple(sorted(c["affectes"])))

# =====================================================
# 1️⃣2️⃣ AFFICHAGE FINAL
# =====================================================
st.subheader("Planning final")

for c in creneaux:
    noms = []
    for b in c["affectes"]:
        noms.extend(b.split("+"))
    noms = list(dict.fromkeys(noms))  # sécurité anti doublon
    places = max_par_creneau - len(noms)
    st.write(f"{c['cle']} → {', '.join(noms)} ({places} place(s))")

# =====================================================
# 1️⃣3️⃣ STATISTIQUES
# =====================================================
st.subheader("Occurrences finales")
for b in blocs:
    st.write(f"{b} : {occ[b]}")
