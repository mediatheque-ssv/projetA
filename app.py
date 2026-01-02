import streamlit as st
import pandas as pd
import random
from datetime import timedelta

st.title("Répartition enfants avec min/max global et binômes")

# =========================
# 1️⃣ Import CSV
# =========================
uploaded_file = st.file_uploader("Importer le CSV (Date ; Horaires ; Noms_dispos)", type=["csv"])
if not uploaded_file:
    st.stop()

df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig", engine="python")
df.columns = [c.replace("\ufeff","").strip() for c in df.columns]

# Nettoyage & parsing des noms
separator = "," if "," in str(df["Noms_dispos"].iloc[0]) else ";"
all_names = sorted({
    n.strip()
    for cell in df["Noms_dispos"]
    if pd.notna(cell)
    for n in str(cell).split(separator)
})

# =========================
# 2️⃣ Paramètres généraux
# =========================
st.subheader("Paramètres de répartition")

col1, col2 = st.columns(2)
with col1:
    min_par_creneau = st.slider("Min enfants par créneau", 1, 10, 4)
    max_par_creneau = st.slider("Max enfants par créneau", min_par_creneau, 10, 5)
with col2:
    delai_min = st.slider("Délai minimum entre 2 présences (jours)", 1, 14, 7)

# =========================
# 3️⃣ Min/max global par enfant
# =========================
st.subheader("Min/Max de chaque enfant")
default_min = [3]*len(all_names)
default_max = [6]*len(all_names)
df_params = pd.DataFrame({
    "Enfant": all_names,
    "Min": default_min,
    "Max": default_max
})
edited_df = st.data_editor(df_params, num_rows="dynamic", use_container_width=True)
enfant_minmax = {row["Enfant"]:(int(row["Min"]), int(row["Max"])) for _, row in edited_df.iterrows()}

# =========================
# 4️⃣ Binômes inséparables
# =========================
st.subheader("Binômes inséparables")
if "binomes" not in st.session_state:
    st.session_state.binomes = []

col1, col2 = st.columns(2)
with col1:
    enfant_a = st.selectbox("Enfant A", all_names, key="bin_a")
with col2:
    enfant_b = st.selectbox("Enfant B", all_names, key="bin_b")

if st.button("Ajouter binôme"):
    if enfant_a != enfant_b and (enfant_a, enfant_b) not in st.session_state.binomes and (enfant_b, enfant_a) not in st.session_state.binomes:
        st.session_state.binomes.append((enfant_a, enfant_b))

if st.session_state.binomes:
    st.write("Binômes définis :")
    for a,b in st.session_state.binomes:
        st.write(f"- {a} + {b}")

# =========================
# 5️⃣ Parsing des dates
# =========================
mois_fr = {'janvier':1,'février':2,'fevrier':2,'mars':3}

def parse_dt(row):
    date_str = str(row['Date']).strip().lower()
    h_str = str(row['Horaires']).strip()
    try:
        jour = int(date_str.split()[1])
        mois = mois_fr[date_str.split()[2]]
        heure = int(h_str.split('h')[0])
        return pd.Timestamp(2026, mois, jour, heure)
    except:
        return pd.Timestamp("1900-01-01")

df['dt'] = df.apply(parse_dt, axis=1)
df_sorted = df.sort_values("dt")

# =========================
# 6️⃣ Préparer les créneaux
# =========================
creneaux = []
for _, row in df_sorted.iterrows():
    if row['dt'] == pd.Timestamp("1900-01-01"):
        continue
    dispos = [n.strip() for n in str(row["Noms_dispos"]).split(separator) if n.strip() in all_names]
    creneaux.append({"cle": f"{row['Date']} | {row['Horaires']}", "dt": row['dt'], "dispos": dispos, "affectes": []})

# =========================
# 7️⃣ Répartition
# =========================
compteur = {nom:0 for nom in all_names}
derniere_presence = {nom:pd.Timestamp("1900-01-01") for nom in all_names}

for c in creneaux:

    # 1️⃣ Placer les binômes
    for a,b in st.session_state.binomes:
        if a in c['dispos'] and b in c['dispos']:
            if (c['dt'] - derniere_presence[a]).days >= delai_min and (c['dt'] - derniere_presence[b]).days >= delai_min:
                if len(c['affectes']) + 2 <= max_par_creneau:
                    if compteur[a] < enfant_minmax[a][1] and compteur[b] < enfant_minmax[b][1]:
                        c['affectes'].extend([a,b])
                        compteur[a] +=1
                        compteur[b] +=1
                        derniere_presence[a] = c['dt']
                        derniere_presence[b] = c['dt']

    # 2️⃣ Placer les autres enfants
    candidats = [n for n in c['dispos'] if n not in c['affectes']]
    random.shuffle(candidats)
    for n in candidats:
        if len(c['affectes']) >= max_par_creneau:
            break
        if compteur[n] >= enfant_minmax[n][1]:
            continue
        if (c['dt'] - derniere_presence[n]).days < delai_min:
            continue
        c['affectes'].append(n)
        compteur[n] +=1
        derniere_presence[n] = c['dt']

# =========================
# 8️⃣ Affichage
# =========================
st.subheader("Planning final")
for c in creneaux:
    st.write(f"{c['cle']} → {', '.join(c['affectes']) if c['affectes'] else '(aucun)'} ({max_par_creneau - len(c['affectes'])} place(s))")

st.subheader("Nombre de présences par enfant")
for nom, cpt in compteur.items():
    st.write(f"{nom}: {cpt}")
