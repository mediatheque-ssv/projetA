import streamlit as st
import pandas as pd
import random
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

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
st.markdown("## 📂 Import du CSV")
uploaded_file = st.file_uploader(
    "Importer le CSV",
    type=["csv"],
    help=(
        "• Le CSV doit contenir exactement les colonnes : 'Date', 'Horaires' et 'Noms_dispos'.  \n"
        "• Chaque nom de bénévole doit être séparé par un point-virgule (Nom1;Nom2;Nom3).  \n"
        "• Pour un binôme, mettre un slash entre les deux noms (Nom1/Nom2).  \n"
        "• Attention à toujours orthographier les noms de la même manière."
    )
)

if uploaded_file:

    # Lecture CSV
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

    # ===========================
    # EXTRACTION DES NOMS
    # ===========================
    sample_cell = str(df["Noms_dispos"].iloc[0]) if len(df) > 0 else ""
    separator = "," if "," in sample_cell else ";"
    
    noms_uniques = sorted({
        n.strip()
        for cell in df["Noms_dispos"]
        if pd.notna(cell)
        for n in str(cell).split(separator)
        if n.strip()
    })

    st.markdown("## 🧒 Enfants et binômes détectés")
    if noms_uniques:
        df_noms = pd.DataFrame(
            {
                "Enfant / binôme": noms_uniques,
                "Type": ["Binôme" if "/" in nom else "Enfant seul" for nom in noms_uniques]
            }
        )
        st.dataframe(df_noms, use_container_width=True, hide_index=True)
        st.info(f"🔎 {len(noms_uniques)} entité(s) détectée(s)")
    else:
        st.warning("Aucun enfant détecté ! Vérifie le CSV")
        st.stop()

    # ===========================
    # CALCUL DES DISPONIBILITÉS
    # ===========================
    def compter_personnes(nom):
        return len(nom.split("/"))
    
    dispos_par_entite = {nom: 0 for nom in noms_uniques}
    for _, row in df.iterrows():
        dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
        dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
        for n in dispos:
            if n in dispos_par_entite:
                dispos_par_entite[n] += 1
    
    # ===========================
    # PARAMÈTRES CRÉNEAUX
    # ===========================
    st.markdown("## ⚙️ Paramètres des créneaux")
    col1, col2 = st.columns(2)
    with col1:
        min_par_date = st.slider("👥 Minimum de personnes par créneau", 1, 10, 4)
    with col2:
        max_par_date = st.slider("👥 Maximum de personnes par créneau", min_par_date, 10, max(5, min_par_date))

    st.markdown("### Contraintes d'occurrences par enfant / binôme")
    
    # Calculer le minimum de disponibilités parmi tous les bénévoles
    min_dispos_total = min(dispos_par_entite.values()) if dispos_par_entite else 0
    
    col3, col4 = st.columns(2)
    with col3:
        min_occurrences = st.slider("🔢 Minimum d'occurrences par enfant/binôme", 0, 10, min_dispos_total)
    with col4:
        max_occurrences = st.slider("🔢 Maximum d'occurrences par enfant/binôme", min_occurrences, 20, 10)
    
    st.markdown("## 📊 Disponibilités par enfant / binôme")
    df_dispos = pd.DataFrame(
        sorted(dispos_par_entite.items(), key=lambda x: x[1]),
        columns=["Enfant / binôme", "Nombre de disponibilités"]
    ).reset_index(drop=True)
    st.dataframe(df_dispos, use_container_width=True, hide_index=True)

    # ===========================
    # INITIALISATION session_state
    # ===========================
    if "repartition" not in st.session_state:
        st.session_state.repartition = None
        st.session_state.output_excel = None
        st.session_state.output_pdf = None
        st.session_state.compteur = None

    # ===========================
    # BOUTON RÉPARTITION
    # ===========================
    st.markdown("## ▶️ Lancer la répartition")
    if st.button("Répartir les enfants"):

        # Fonction pour effectuer une répartition complète
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

            # Affectation en plusieurs passes pour atteindre les minimums
            MAX_PASSES = 5
            for passe in range(MAX_PASSES):
                amelioration = False
                
                for creneau in creneaux_info:
                    date_horaire_dt = creneau['dt']
                    dispos = creneau['dispos']
                    nb_personnes_affectees = sum(compter_personnes(n) for n in creneau['affectes'])
                    
                    # Si le créneau est plein, on passe au suivant
                    if nb_personnes_affectees >= max_par_date:
                        continue
                    
                    candidats = []
                    for n in dispos:
                        if n not in creneau['affectes']:
                            # Vérifier si l'enfant n'a pas déjà atteint le maximum d'occurrences
                            if compteur[n] >= max_occurrences:
                                continue
                            
                            distance = min([(date_horaire_dt - d).days for d in affectations[n]] + [float('inf')])
                            if distance >= DELAI_MINIMUM:
                                nb_dispos = dispos_par_entite[n]
                                # Bonus pour ceux qui ont peu de disponibilités
                                bonus = -100 if nb_dispos < 5 else 0
                                # GROS bonus pour ceux en dessous du minimum d'occurrences
                                if compteur[n] < min_occurrences:
                                    bonus -= 1000
                                alea_compteur = random.uniform(-0.5, 0.5)
                                alea_dispos = random.uniform(-1, 1)
                                candidats.append((n, compteur[n] + bonus + alea_compteur, nb_dispos + alea_dispos))
                    
                    candidats.sort(key=lambda x: (x[1], x[2]))
                    for nom, _, _ in candidats:
                        nb_personnes_ce_nom = compter_personnes(nom)
                        if nb_personnes_affectees + nb_personnes_ce_nom <= max_par_date:
                            creneau['affectes'].append(nom)
                            compteur[nom] += 1
                            affectations[nom].append(date_horaire_dt)
                            nb_personnes_affectees += nb_personnes_ce_nom
                            amelioration = True
                
                # Si on n'a rien pu améliorer, on arrête les passes
                if not amelioration:
                    break
            
            return creneaux_info, compteur

        # Lancer jusqu'à 50 tentatives pour trouver une répartition parfaite
        MAX_TENTATIVES = 50
        meilleure_repartition = None
        meilleur_compteur = None
        meilleur_score = float('inf')  # Score de pénalité global
        
        with st.spinner(f'🔄 Recherche de la meilleure répartition (max {MAX_TENTATIVES} tentatives)...'):
            for tentative in range(MAX_TENTATIVES):
                creneaux_info, compteur = faire_repartition()
                
                # Calculer le score de pénalité
                score = 0
                
                # Pénalité pour les enfants hors contraintes min/max occurrences
                for nom, count in compteur.items():
                    if count < min_occurrences:
                        score += (min_occurrences - count) * 10  # Pénalité forte
                    if count > max_occurrences:
                        score += (count - max_occurrences) * 10  # Pénalité forte
                
                # Pénalité pour les créneaux qui n'atteignent pas le maximum
                for creneau in creneaux_info:
                    enfants_affichage = []
                    for e in creneau['affectes']:
                        enfants_affichage.extend(e.split("/"))
                    nb_personnes = len(enfants_affichage)
                    
                    if nb_personnes < max_par_date:
                        score += (max_par_date - nb_personnes) * 5  # Pénalité moyenne
                
                # Garder la meilleure tentative
                if score < meilleur_score:
                    meilleur_score = score
                    meilleure_repartition = creneaux_info
                    meilleur_compteur = compteur
                
                # Si on a trouvé une répartition parfaite (score = 0), on s'arrête
                if score == 0:
                    st.success(f'✅ Répartition parfaite trouvée en {tentative + 1} tentative(s) !')
                    break
            else:
                # Si on arrive ici, aucune répartition parfaite n'a été trouvée
                if meilleur_score > 0:
                    st.info(f'ℹ️ Meilleure répartition trouvée après {MAX_TENTATIVES} tentatives (certaines contraintes ne peuvent pas être respectées).')

        creneaux_info = meilleure_repartition
        compteur = meilleur_compteur

        creneaux_info = meilleure_repartition
        compteur = meilleur_compteur

        # Vérifier et afficher toutes les contraintes
        enfants_sous_minimum = {nom: count for nom, count in compteur.items() if count < min_occurrences}
        enfants_sur_maximum = {nom: count for nom, count in compteur.items() if count > max_occurrences}
        
        creneaux_sous_minimum = []
        for creneau in creneaux_info:
            enfants_affichage = []
            for e in creneau['affectes']:
                enfants_affichage.extend(e.split("/"))
            nb_personnes = len(enfants_affichage)
            if nb_personnes < min_par_date:
                creneaux_sous_minimum.append((creneau['cle'], nb_personnes))
        
        if enfants_sous_minimum:
            st.warning(f"⚠️ {len(enfants_sous_minimum)} enfant(s)/binôme(s) n'ont pas atteint le minimum de {min_occurrences} occurrence(s) :")
            for nom, count in enfants_sous_minimum.items():
                st.write(f"• {nom} : {count} occurrence(s)")
            st.info("💡 Essayez d'augmenter le nombre maximum de personnes par créneau ou de réduire le minimum d'occurrences.")
        
        if enfants_sur_maximum:
            st.warning(f"⚠️ {len(enfants_sur_maximum)} enfant(s)/binôme(s) ont dépassé le maximum de {max_occurrences} occurrence(s) :")
            for nom, count in enfants_sur_maximum.items():
                st.write(f"• {nom} : {count} occurrence(s)")
            st.info("💡 Essayez d'augmenter le maximum d'occurrences ou de réduire le nombre maximum de personnes par créneau.")
        
        if creneaux_sous_minimum:
            st.warning(f"⚠️ {len(creneaux_sous_minimum)} créneau(x) n'ont pas atteint le minimum de {min_par_date} personne(s) :")
            for cle, nb in creneaux_sous_minimum:
                st.write(f"• {cle} : {nb} personne(s)")
            st.info("💡 Vérifiez les disponibilités ou réduisez le minimum de personnes par créneau.")

        # Stocker dans session_state
        st.session_state.repartition = creneaux_info
        st.session_state.compteur = compteur

        # ===========================
        # EXPORT EXCEL
        # ===========================
        export_df = pd.DataFrame([
            {
                "DATE": creneau['cle'].split(" | ")[0],
                "HORAIRES": creneau['cle'].split(" | ")[1],
                "NOMS DES MINI-BÉNÉVOLES": ", ".join([n for e in creneau['affectes'] for n in e.split("/")])
            }
            for creneau in creneaux_info
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
        # EXPORT PDF
        # ===========================
        output_pdf = io.BytesIO()
        c = canvas.Canvas(output_pdf, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica", 12)
        data = [["DATE", "HORAIRES", "NOMS DES MINI-BÉNÉVOLES"]]
        for r in creneaux_info:
            data.append([r['cle'].split(" | ")[0], r['cle'].split(" | ")[1],
                         ", ".join([n for e in r['affectes'] for n in e.split("/")])])
        # Calcul hauteur automatique pour tenir sur une page
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
# AFFICHAGE RÉPARTITION ET BOUTONS
# ===========================
if st.session_state.get("repartition"):
    repartition = st.session_state.repartition
    compteur = st.session_state.compteur
    st.markdown("## 🧩 Répartition finale")
    for creneau in repartition:
        enfants_affichage = []
        for e in creneau['affectes']:
            enfants_affichage.extend(e.split("/"))
        nb_personnes = len(enfants_affichage)
        st.write(f"{creneau['cle']} : {', '.join(enfants_affichage)} ({max_par_date - nb_personnes} place(s) restante(s))")

    # Affichage occurrences
    st.markdown("## 🔁 Occurrences par enfant / binôme")
    compteur_sorted = dict(sorted(compteur.items(), key=lambda x: x[1]))
    df_occ = pd.DataFrame(compteur_sorted.items(), columns=["Enfant / binôme", "Nombre d'occurrences"])
    st.dataframe(df_occ, use_container_width=True, hide_index=True)

    col_excel, col_pdf = st.columns(2)
    with col_excel:
        st.download_button(
            "Télécharger le tableau (Excel)",
            data=st.session_state.output_excel.getvalue(),
            file_name="repartition.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col_pdf:
        st.download_button(
            "Télécharger le tableau (PDF)",
            data=st.session_state.output_pdf.getvalue(),
            file_name="repartition.pdf",
            mime="application/pdf"
        )
