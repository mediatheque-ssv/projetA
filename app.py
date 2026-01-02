import streamlit as st
import pandas as pd
import random
from collections import Counter
from datetime import datetime

st.title("Répartition enfants avec binômes et min/max équilibré")

# -----------------------------
# 1️⃣ Upload CSV de disponibilités
# -----------------------------
uploaded_file = st.file_uploader(
    "Importer le CSV (Excel FR – séparateur ;) avec colonnes Date,Horaires,Noms_dispos",
    type=["csv"]
)

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8")
    df["Noms_dispos"] = df["Noms_dispos"].apply(lambda x: x.split(";"))

    # -----------------------------
    # Fonction parsing date/heure robuste
    # -----------------------------
    def parse_datetime(row):
        date_str = row['Date'].strip()
        time_str = row['Horaires'].strip().replace(' ', '').replace('h', ':')
        if ':' not in time_str:
            time_str += ':00'
        else:
            parts = time_str.split(':')
            if len(parts) == 2:
                if parts[1] == '' or len(parts[1]) == 1:
                    parts[1] = parts[1].ljust(2, '0')
                time_str = ':'.join(parts)
            else:
                time_str = parts[0] + ':00'
        full_str = f"{date_str} {time_str}"
        return datetime.strptime(full_str, "%d/%m/%Y %H:%M")

    df['Datetime'] = df.apply(parse_datetime, axis=1)

    # -----------------------------
    # 2️⃣ Détection des enfants
    # -----------------------------
    all_children = sorted(set(c for sublist in df["Noms_dispos"] for c in sublist))
    st.write(f"Enfants détectés ({len(all_children)}) :", all_children)

    # -----------------------------
    # 3️⃣ Paramètres
    # -----------------------------
    st.subheader("Paramètres généraux")
    min_per_slot = st.number_input("Min enfants par créneau", min_value=1, max_value=10, value=4)
    max_per_slot = st.number_input("Max enfants par créneau", min_value=1, max_value=10, value=5)
    min_global = st.number_input("Min occurrences par enfant (global)", min_value=0, max_value=20, value=3)
    max_global = st.number_input("Max occurrences par enfant (global)", min_value=1, max_value=20, value=6)

    st.subheader("Binômes (inséparables)")
    binomes_text = st.text_area(
        "Entrez les binômes séparés par une virgule et un retour à la ligne pour chaque binôme, exemple :\nHugo,Théo\nMaïwenn,Sterenn",
        height=100
    )
    binomes = []
    for line in binomes_text.split("\n"):
        parts = [x.strip() for x in line.split(",") if x.strip()]
        if len(parts) >= 2:
            binomes.append(parts)

    # Mapping enfant -> binôme
    child_to_binome = {}
    for b in binomes:
        for child in b:
            child_to_binome[child] = b

    # -----------------------------
    # 4️⃣ Génération planning
    # -----------------------------
    def generate_schedule(df, min_per_slot, max_per_slot, min_global, max_global):
        schedule = []
        global_counter = Counter({child: 0 for child in all_children})

        # Tri chronologique
        df_sorted = df.sort_values("Datetime").reset_index(drop=True)

        for idx, row in df_sorted.iterrows():
            date, time, dispo = row["Date"], row["Horaires"], row["Noms_dispos"]
            dispo = set(dispo)
            # Retirer ceux qui ont atteint max global
            dispo = [c for c in dispo if global_counter[c] < max_global]

            # Gestion binômes : si un membre est dispo, tous doivent être dispo et pas maxés
            def binome_check(c):
                if c in child_to_binome:
                    return all(member in dispo and global_counter[member] < max_global for member in child_to_binome[c])
                return True

            dispo = [c for c in dispo if binome_check(c)]
            # Priorité aux enfants les moins affectés
            dispo.sort(key=lambda x: global_counter[x])

            slot = []
            for child in dispo:
                if child in slot:
                    continue
                # Ajouter le binôme complet si nécessaire
                if child in child_to_binome:
                    members = child_to_binome[child]
                    if all(member not in slot for member in members):
                        if len(slot) + len(members) <= max_per_slot:
                            slot.extend(members)
                            for m in members:
                                global_counter[m] += 1
                else:
                    if len(slot) < max_per_slot:
                        slot.append(child)
                        global_counter[child] += 1
                if len(slot) >= max_per_slot:
                    break

            # Remplir min_per_slot si nécessaire
            if len(slot) < min_per_slot:
                for child in dispo:
                    if child not in slot and len(slot) < min_per_slot:
                        slot.append(child)
                        global_counter[child] += 1

            schedule.append({
                "Date": date,
                "Horaires": time,
                "Enfants": slot,
                "Places_restantes": max_per_slot - len(slot)
            })

        return schedule

    # -----------------------------
    # 5️⃣ Bouton génération
    # -----------------------------
    if st.button("Générer le planning équilibré"):
        schedule = generate_schedule(df, min_per_slot, max_per_slot, min_global, max_global)

        st.subheader("Planning final")
        for s in schedule:
            st.write(f"{s['Date']} | {s['Horaires']} → {', '.join(s['Enfants'])} ({s['Places_restantes']} place(s))")

        # Occurrences par enfant
        st.subheader("Occurrences par enfant")
        total_counter = Counter()
        for s in schedule:
            for c in s['Enfants']:
                total_counter[c] += 1
        df_counter = pd.DataFrame({"Enfant": list(total_counter.keys()), "Occurrences": list(total_counter.values())})
        st.dataframe(df_counter.sort_values("Occurrences"))

        # Export CSV
        csv = pd.DataFrame(schedule)
        csv["Enfants"] = csv["Enfants"].apply(lambda x: ";".join(x))
        st.download_button("Exporter CSV", csv.to_csv(index=False, sep=";"), "planning.csv", "text/csv")
