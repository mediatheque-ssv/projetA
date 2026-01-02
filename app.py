import streamlit as st
import pandas as pd
import random
from collections import defaultdict, Counter
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

    # Conversion Date + Horaires en datetime pour tri automatique
    def parse_datetime(row):
        return datetime.strptime(f"{row['Date']} {row['Horaires'].replace('h',':00')}", "%d/%m/%Y %H:%M")

    df['Datetime'] = df.apply(parse_datetime, axis=1)
    df = df.sort_values('Datetime').reset_index(drop=True)

    # Récupération de tous les enfants
    all_children = sorted({c for sublist in df["Noms_dispos"] for c in sublist})
    st.write(f"Enfants détectés ({len(all_children)}) :", all_children)

    # -----------------------------
    # 2️⃣ Paramètres
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

    # Mapping enfant → binôme(s)
    child_to_binome = {}
    for b in binomes:
        for child in b:
            child_to_binome[child] = b

    # -----------------------------
    # 3️⃣ Génération planning
    # -----------------------------
    def generate_schedule(df, min_per_slot, max_per_slot, min_global, max_global):
        schedule = []
        global_counter = Counter({child: 0 for child in all_children})

        for idx, row in df.iterrows():
            date, time, dispo = row["Date"], row["Horaires"], row["Noms_dispos"]
            dispo = set(dispo)

            # Enfants déjà au max global
            dispo = [c for c in dispo if global_counter[c] < max_global]

            # Vérifie si binôme complet dispo
            def binome_check(c):
                if c in child_to_binome:
                    return all(member in dispo and global_counter[member] < max_global for member in child_to_binome[c])
                return True

            dispo = [c for c in dispo if binome_check(c)]

            # Priorité aux enfants les moins affectés globalement
            dispo.sort(key=lambda x: global_counter[x])

            slot = []
            for child in dispo:
                if child in slot:
                    continue
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

            # Remplir pour atteindre min_per_slot si possible
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

        # Tri final par datetime (pour sécurité)
        schedule.sort(key=lambda x: datetime.strptime(f"{x['Date']} {x['Horaires'].replace('h',':00')}", "%d/%m/%Y %H:%M"))
        return schedule

    if st.button("Générer le planning équilibré"):
        schedule = generate_schedule(df, min_per_slot, max_per_slot, min_global, max_global)
        st.subheader("Planning final")
        for s in schedule:
            st.write(f"{s['Date']} | {s['Horaires']} → {', '.join(s['Enfants'])} ({s['Places_restantes']} place(s))")

        # Statistiques globales
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
