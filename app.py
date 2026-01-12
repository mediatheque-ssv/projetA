import streamlit as st
import pandas as pd
import random
import io
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# ===========================
# FONCTIONS
# ===========================
def dataframe_left(df, colonne):
    return df.style.set_properties(
        subset=[colonne],
        **{"text-align": "left"}
    )

def compter_personnes(nom):
    return len(nom.split("/"))

def dataframe_left_all(df):
    return df.style.set_properties(
        **{"text-align": "left"}
    )

# ===========================
# STYLE
# ===========================
st.markdown("""
<style>
.stMarkdown p { font-size: 14px; }
.stButton>button {
    background-color: #6D28D9;
    color: white;
    border-radius: 12px;
    padding: 0.6em 1.2em;
    font-size: 1.05em;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #5B21B6;
    color: white;
}

/* Bouton Excel vert - première colonne */
div[data-testid="column"]:first-child .stDownloadButton button {
    background-color: #107C41;
    color: white;
    border-radius: 12px;
    padding: 0.6em 1.2em;
    font-size: 1.05em;
    font-weight: 600;
}
div[data-testid="column"]:first-child .stDownloadButton button:hover {
    background-color: #0D5C2F;
    color: white;
}

/* Bouton PDF rouge - deuxième colonne */
div[data-testid="column"]:last-child .stDownloadButton button {
    background-color: #DC2626;
    color: white;
    border-radius: 12px;
    padding: 0.6em 1.2em;
    font-size: 1.05em;
    font-weight: 600;
}
div[data-testid="column"]:last-child .stDownloadButton button:hover {
    background-color: #B91C1C;
    color: white;
}

hr { border: none; height: 2px; background-color: #DDD6FE; margin: 1.5em 0; }
</style>

<h1 style="
    color: #6D28D9; 
    font-size: 2.5em; 
    font-weight: 800; 
    text-align: center; 
    margin-bottom: 0.5em;
    font-variant: small-caps;
">
répartition mini-bénévoles
</h1>
""", unsafe_allow_html=True)

# ===========================
# IMPORT CSV
# ===========================
st.markdown("### 📂 Import du CSV")
uploaded_file = st.file_uploader(
    "Importer le CSV",
    type=["csv"],
    help=(
        "• Le CSV doit contenir exactement les colonnes : 'Date', 'Horaires' et 'Noms_dispos'.  \n"
        "• Chaque nom de bénévole doit être séparé par un point-virgule (Nom1;Nom2;Nom3).  \n"
        "• Pour indiquer un binôme, mettre un slash entre les deux noms (Nom1/Nom2).  \n"
        "• Ne pas noter une personne comme disponible sur un créneau si son binôme n'est pas disponible sur ce même créneau.  \n"
        "• Attention à toujours orthographier les noms de la même manière."
    )
)

noms_uniques = []

if uploaded_file:
    # ---------------------------
    # Lecture CSV + extraction noms
    # ---------------------------
    with st.spinner("⏳ Lecture et traitement du CSV…"):
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

        sample_cell = str(df["Noms_dispos"].iloc[0]) if len(df) > 0 else ""
        separator = "," if "," in sample_cell else ";"
        noms_uniques = sorted({
            n.strip()
            for cell in df["Noms_dispos"]
            if pd.notna(cell)
            for n in str(cell).split(separator)
            if n.strip()
        })

    # ---------------------------
    # Calcul disponibilités
    # ---------------------------
    with st.spinner("⏳ Calcul des disponibilités…"):
        dispos_par_entite = {nom: 0 for nom in noms_uniques}
        for _, row in df.iterrows():
            dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
            dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
            for n in dispos:
                if n in dispos_par_entite:
                    dispos_par_entite[n] += 1

    # ---------------------------
    # Affichage enfants / binômes
    # ---------------------------
    st.markdown("### 🧒 Enfants et binômes détectés")
    if noms_uniques:
        with st.spinner("⏳ Analyse du fichier…"):
            df_noms = pd.DataFrame(
                {
                    "Enfant / binôme": noms_uniques,
                    "Type": ["Binôme" if "/" in nom else "Enfant seul" for nom in noms_uniques],
                    "Nombre de disponibilités": [dispos_par_entite[n] for n in noms_uniques]
                }
            ).sort_values("Nombre de disponibilités").reset_index(drop=True)
            df_noms["Nombre de disponibilités"] = df_noms["Nombre de disponibilités"].astype(str)
            st.dataframe(dataframe_left(df_noms, "Nombre de disponibilités"), use_container_width=True, hide_index=True)
            st.info(f"🔎 {len(noms_uniques)} entité(s) détectée(s)")
    else:
        st.warning("Aucun enfant détecté ! Vérifie le CSV")
        st.stop()

    # ---------------------------
    # Paramètres créneaux
    # ---------------------------
    st.markdown("### ⚙️ Paramètres des créneaux")
    col1, col2 = st.columns(2)
    with col1:
        min_par_date = st.slider("👥 Minimum de mini-b par créneau", 1, 10, 4)
    with col2:
        max_par_date = st.slider("👥 Maximum de mini-b par créneau", min_par_date, 10, max(5, min_par_date))
    
    min_dispos_total = min(dispos_par_entite.values()) if dispos_par_entite else 0
    col3, col4 = st.columns(2)
    with col3:
        min_occurrences = st.slider("🔢 Minimum d'occurrences par mini-b", 0, 10, min_dispos_total)
    with col4:
        max_occurrences = st.slider("🔢 Maximum d'occurrences par mini-b", min_occurrences, 20, 5)

    # ---------------------------
    # Initialisation session_state
    # ---------------------------
    if "repartition" not in st.session_state:
        st.session_state.repartition = None
        st.session_state.output_excel = None
        st.session_state.output_pdf = None
        st.session_state.compteur = None

    # ---------------------------
    # Bouton Répartition
    # ---------------------------
    st.markdown("### 🪄 Élaboration du planning")
    if st.button("✨ Clic magique ✨"):
        with st.spinner("⏳ Calcul de la meilleure répartition…"):
            # Fonction principale
            def faire_repartition():
                compteur = {nom: 0 for nom in noms_uniques}
                affectations = {nom: [] for nom in noms_uniques}
                DELAI_MINIMUM = 6
                mois_fr = {
                    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
                }

                def parse_dt(row):
                    try:
                        date_str = str(row['Date']).strip().lower()
                        horaire_str = str(row['Horaires']).strip()
                        parts = date_str.split()
                        jour = int(parts[1]) if len(parts) > 1 else 1
                        mois_nom = parts[2] if len(parts) > 2 else 'janvier'
                        mois = mois_fr.get(mois_nom, 1)
                        horaire_str = horaire_str.replace('h', ':00') if 'h' in horaire_str else horaire_str
                        heure = int(horaire_str.split(':')[0]) if ':' in horaire_str else 0
                        minute = int(horaire_str.split(':')[1]) if ':' in horaire_str and len(horaire_str.split(':')) > 1 else 0
                        return pd.Timestamp(year=2026, month=mois, day=jour, hour=heure, minute=minute)
                    except:
                        return pd.to_datetime("1900-01-01 00:00")

                df_sorted = df.copy()
                df_sorted['dt'] = df_sorted.apply(parse_dt, axis=1)
                df_sorted = df_sorted.sort_values("dt")

                creneaux_info = []
                for _, row in df_sorted.iterrows():
                    date = str(row["Date"]).strip() or "1900-01-01"
                    horaire = str(row["Horaires"]).strip() or "00:00"
                    horaire_export = "10h - 11h" if horaire.startswith("10") else "15h - 16h" if horaire.startswith("15") else horaire
                    dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
                    dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
                    dispos = [n for n in dispos if n in compteur]
                    cle = f"{date} | {horaire_export}"
                    creneaux_info.append({'cle': cle, 'dt': row['dt'], 'dispos': dispos, 'affectes': []})

                # Passes multiples
                MAX_PASSES = 5
                for passe in range(MAX_PASSES):
                    amelioration = False
                    for creneau in creneaux_info:
                        date_horaire_dt = creneau['dt']
                        nb_personnes_affectees = sum(compter_personnes(n) for n in creneau['affectes'])
                        if nb_personnes_affectees >= max_par_date:
                            continue
                        candidats = []
                        for n in creneau['dispos']:
                            if n not in creneau['affectes'] and compteur[n] < max_occurrences:
                                distance = min([(date_horaire_dt - d).days for d in affectations[n]] + [float('inf')])
                                if distance >= DELAI_MINIMUM:
                                    nb_dispos = dispos_par_entite[n]
                                    bonus = -100 if nb_dispos < 5 else 0
                                    if compteur[n] < min_occurrences:
                                        bonus -= 1000
                                    alea_compteur = random.uniform(-0.5, 0.5)
                                    alea_dispos = random.uniform(-1, 1)
                                    candidats.append((n, compteur[n]+bonus+alea_compteur, nb_dispos+alea_dispos))
                        candidats.sort(key=lambda x: (x[1], x[2]))
                        for nom, _, _ in candidats:
                            nb_personnes_ce_nom = compter_personnes(nom)
                            if nb_personnes_affectees + nb_personnes_ce_nom <= max_par_date:
                                creneau['affectes'].append(nom)
                                compteur[nom] += 1
                                affectations[nom].append(date_horaire_dt)
                                nb_personnes_affectees += nb_personnes_ce_nom
                                amelioration = True
                    if not amelioration:
                        break
                return creneaux_info, compteur

            # Plusieurs tentatives
            MAX_TENTATIVES = 100
            meilleure_repartition = None
            meilleur_compteur = None
            meilleur_score = float('inf')

            for tentative in range(MAX_TENTATIVES):
                creneaux_info, compteur = faire_repartition()
                score = 0
                for nom, count in compteur.items():
                    if count < min_occurrences:
                        score += (min_occurrences - count)*10
                    if count > max_occurrences:
                        score += (count - max_occurrences)*10
                for creneau in creneaux_info:
                    nb_p = sum(len(e.split("/")) for e in creneau['affectes'])
                    if nb_p < min_par_date:
                        score += (min_par_date - nb_p)*5
                if score < meilleur_score:
                    meilleur_score = score
                    meilleure_repartition = creneaux_info
                    meilleur_compteur = compteur
                if score == 0:
                    st.success(f'✅ Répartition parfaite trouvée en {tentative+1} tentative(s) !')
                    break
            else:
                if meilleur_score > 0:
                    st.info(f"ℹ️ Meilleure répartition trouvée après {MAX_TENTATIVES} tentatives.")

            # Stockage
            st.session_state.repartition = meilleure_repartition
            st.session_state.compteur = meilleur_compteur

            # ===========================
            # Export Excel
            # ===========================
            with st.spinner("⏳ Préparation du fichier Excel…"):
                export_df = pd.DataFrame([
                    {
                        "DATE": creneau['cle'].split(" | ")[0],
                        "HORAIRES": creneau['cle'].split(" | ")[1],
                        "NOMS DES MINI-BÉNÉVOLES": ", ".join([n for e in creneau['affectes'] for n in e.split("/")])
                    }
                    for creneau in st.session_state.repartition
                ])
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                    export_df.to_excel(writer, index=False, sheet_name="Répartition")
                    workbook = writer.book
                    worksheet = writer.sheets["Répartition"]
                    header_format = workbook.add_format({'bold': True,'valign':'vcenter','align':'center','bg_color':'#F2CEEF','border':1})
                    cell_format = workbook.add_format({'valign':'vcenter','align':'center','border':1})
                    for col_num, value in enumerate(export_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                        for row_num, val in enumerate(export_df[value], start=1):
                            worksheet.write(row_num, col_num, val, cell_format)
                        max_len = max(export_df[value].astype(str).map(len).max(), len(value)) + 2
                        worksheet.set_column(col_num, col_num, max_len)
                    worksheet.set_row(0, 40)
                    for row in range(1, len(export_df)+1):
                        worksheet.set_row(row, 35)
                st.session_state.output_excel = output_excel

            # ===========================
            # Export PDF
            # ===========================
            with st.spinner("⏳ Préparation du fichier PDF…"):
                output_pdf = io.BytesIO()
                c = canvas.Canvas(output_pdf, pagesize=A4)
                width, height = A4
                c.setFont("Helvetica", 12)
                data = [["DATE", "HORAIRES", "NOMS DES MINI-BÉNÉVOLES"]]
                for r in st.session_state.repartition:
                    data.append([r['cle'].split(" | ")[0], r['cle'].split(" | ")[1],
                                 ", ".join([n for e in r['affectes'] for n in e.split("/")])])
                available_height = height - 100
                row_height = available_height / len(data)
                table = Table(data, colWidths=[120, 80, 300], rowHeights=row_height)
                style = TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F2CEEF')),
                    ('TEXTCOLOR',(0,0),(-1,0),colors.black),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                    ('GRID',(0,0),(-1,-1),1,colors.black),
                    ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')
                ])
                table.setStyle(style)
                table.wrapOn(c, width, height)
                table.drawOn(c, 30, height - 50 - row_height*len(data))
                c.showPage()
                c.save()
                output_pdf.seek(0)
                st.session_state.output_pdf = output_pdf

# ===========================
# Affichage répartition et téléchargement
# ===========================
if st.session_state.get("repartition"):
    repartition = st.session_state.repartition
    compteur = st.session_state.compteur

    # Occurrences
    st.markdown("#### Occurrences par enfant / binôme")
    compteur_sorted = dict(sorted(compteur.items(), key=lambda x: x[1]))
    df_occ = pd.DataFrame(compteur_sorted.items(), columns=["Enfant / binôme", "Nombre d'occurrences"])
    df_occ["Nombre d'occurrences"] = df_occ["Nombre d'occurrences"].astype(str)
    st.dataframe(dataframe_left(df_occ, "Nombre d'occurrences"), use_container_width=True, hide_index=True)

    # ===========================
    # RÉPARTITION FINALE STYLÉE
    # ===========================
    st.markdown("#### Répartition proposée")
    creneaux_display = []

    for creneau in repartition:
        enfants_affichage = []
        for e in creneau['affectes']:
            enfants_affichage.extend(e.split("/"))
        nb_personnes = len(enfants_affichage)
        places_restantes = max_par_date - nb_personnes

        creneaux_display.append({
            "Date": creneau['cle'].split(" | ")[0],
            "Horaire": creneau['cle'].split(" | ")[1],
            "Enfants présents": ", ".join(enfants_affichage),
            "Places restantes": str(places_restantes)
        })

    df_final = pd.DataFrame(creneaux_display)

    def style_final_repartition(df):
        def color_row(row):
            if row["Places restantes"] == "0":
                return ["background-color: #D1FAE5"]*len(row)
            elif int(row["Places restantes"]) > max_par_date - min_par_date:
                return ["background-color: #FEE2E2"]*len(row)
            else:
                return ["background-color: #F9F9F9"]*len(row)

        styled = df.style.apply(color_row, axis=1)
        styled = styled.set_properties(subset=["Places restantes"], **{"text-align": "left"})
        return styled

    st.dataframe(
        style_final_repartition(df_final),
        use_container_width=True,
        hide_index=True
    )

    # Boutons téléchargement avec HTML personnalisé
    col_excel, col_pdf = st.columns(2)
    
    with col_excel:
        if st.session_state.get("output_excel"):
            b64_excel = base64.b64encode(st.session_state.output_excel.getvalue()).decode()
            st.markdown(f"""
            <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="repartition.xlsx" style="text-decoration:none;">
                <button style="background-color:#107C41;color:white;padding:0.6em 1.2em;border-radius:12px;font-weight:400;font-size:1.05em;border:none;cursor:pointer;width:100%;">
                    Télécharger le planning (Excel)
                </button>
            </a>
            """, unsafe_allow_html=True)
    
    with col_pdf:
        if st.session_state.get("output_pdf"):
            b64_pdf = base64.b64encode(st.session_state.output_pdf.getvalue()).decode()
            st.markdown(f"""
            <a href="data:application/pdf;base64,{b64_pdf}" download="repartition.pdf" style="text-decoration:none;">
                <button style="background-color:#DC2626;color:white;padding:0.6em 1.2em;border-radius:12px;font-weight:400;font-size:1.05em;border:none;cursor:pointer;width:100%;">
                    Télécharger le planning (PDF)
                </button>
            </a>
            """, unsafe_allow_html=True)
