import streamlit as st
import pandas as pd
import random
import io
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

st.markdown("""
<style>
.stMarkdown p {
    font-size: 14px;
}
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

st.markdown("""
<style>
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
hr {
    border: none;
    height: 2px;
    background-color: #DDD6FE;
    margin: 1.5em 0;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 1️⃣ IMPORT DU CSV
# =====================================================
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

    # =====================================================
    # 2️⃣ EXTRACTION DES NOMS (avec binômes groupés)
    # =====================================================
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
        df_noms = pd.DataFrame({
            "Enfant / binôme": noms_uniques,
            "Type": ["Binôme" if "/" in nom else "Enfant seul" for nom in noms_uniques]
        })
        st.dataframe(df_noms, use_container_width=True, hide_index=True)
        st.info(f"🔎 {len(noms_uniques)} entité(s) détectée(s)")
    else:
        st.warning("Aucun enfant détecté ! Vérifie le CSV")
        st.stop()

    # =====================================================
    # 3️⃣ PARAMÈTRES DES CRÉNEAUX
    # =====================================================
    st.markdown("## ⚙️ Paramètres des créneaux")
    col1, col2 = st.columns(2)
    with col1:
        min_par_date = st.slider(
            "👥 Minimum de personnes par créneau",
            min_value=1,
            max_value=10,
            value=4
        )
    with col2:
        max_par_date = st.slider(
            "👥 Maximum de personnes par créneau",
            min_value=min_par_date,
            max_value=10,
            value=max(5, min_par_date)
        )

    # =====================================================
    # 4️⃣ CALCUL DES DISPONIBILITÉS
    # =====================================================
    def compter_personnes(nom):
        return len(nom.split("/"))
    
    dispos_par_entite = {nom: 0 for nom in noms_uniques}
    for _, row in df.iterrows():
        dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
        dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
        for n in dispos:
            if n in dispos_par_entite:
                dispos_par_entite[n] += 1

    st.markdown("## 📊 Disponibilités par enfant / binôme")
    df_dispos = pd.DataFrame(
        sorted(dispos_par_entite.items(), key=lambda x: x[1]),
        columns=["Enfant / binôme", "Nombre de disponibilités"]
    ).reset_index(drop=True)
    st.dataframe(df_dispos, use_container_width=True, hide_index=True)

    # =====================================================
    # 5️⃣ RÉPARTITION AUTOMATIQUE
    # =====================================================
    st.markdown("## ▶️ 5. Lancer la répartition")
    if st.button("Répartir les enfants"):

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
            if horaire.startswith("10"):
                horaire_export = "10h - 11h"
            elif horaire.startswith("15"):
                horaire_export = "15h - 16h"
            else:
                horaire_export = horaire
            dispos_raw = str(row["Noms_dispos"]) if pd.notna(row["Noms_dispos"]) else ""
            dispos = [n.strip() for n in dispos_raw.split(separator) if n.strip()]
            dispos = [n for n in dispos if n in compteur]
            cle = f"{date} | {horaire_export}"
            creneaux_info.append({'cle': cle, 'dt': row['dt'], 'dispos': dispos, 'affectes': []})

        # Affectation
        for creneau in creneaux_info:
            date_horaire_dt = creneau['dt']
            dispos = creneau['dispos']
            nb_personnes_affectees = sum(compter_personnes(n) for n in creneau['affectes'])
            candidats = []
            for n in dispos:
                if n not in creneau['affectes']:
                    distance = min([(date_horaire_dt - d).days for d in affectations[n]] + [float('inf')])
                    if distance >= DELAI_MINIMUM:
                        nb_dispos = dispos_par_entite[n]
                        bonus = -100 if nb_dispos < 5 else 0
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

        st.session_state['creneaux_info'] = creneaux_info  # sauvegarde pour téléchargement

        # =====================================================
        # 6️⃣ AFFICHAGE FINAL
        # =====================================================
        st.markdown("## 🧩 Répartition finale")
        for c in creneaux_info:
            enfants_raw = c['affectes']
            enfants_affichage = []
            for e in enfants_raw:
                enfants_affichage.extend(e.split("/"))
            nb_personnes = len(enfants_affichage)
            st.write(f"{c['cle']} : {', '.join(enfants_affichage) if enfants_affichage else 'Aucun'} "
                     f"({max_par_date - nb_personnes} place(s) restante(s))")

        # Occurrences
        st.markdown("## 🔁 Occurrences par enfant / binôme")
        compteur_sorted = dict(sorted(compteur.items(), key=lambda x: x[1]))
        df_occ = pd.DataFrame(compteur_sorted.items(), columns=["Enfant / binôme", "Nombre d'occurrences"])
        st.dataframe(df_occ, use_container_width=True, hide_index=True)

        # Jamais affectés
        jamais_affectes = [nom for nom, c in compteur.items() if c == 0]
        if jamais_affectes:
            st.markdown("## ⚠️ Enfants / binômes jamais affectés")
            st.write(", ".join(jamais_affectes))

        # =====================================================
        # 7️⃣ BOUTONS DE TÉLÉCHARGEMENT (Excel + PDF côte à côte)
        # =====================================================
        export_df = pd.DataFrame([
            {
                "DATE": c['cle'].split(" | ")[0],
                "HORAIRES": c['cle'].split(" | ")[1],
                "NOMS DES MINI-BÉNÉVOLES": ", ".join([n for e in c['affectes'] for n in e.split("/")])
            }
            for c in creneaux_info
        ])

        col_excel, col_pdf = st.columns(2)

        # --- Excel ---
        with col_excel:
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, index=False, sheet_name="Répartition")
                workbook = writer.book
                worksheet = writer.sheets["Répartition"]
                header_format = workbook.add_format({
                    'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
                    'bg_color': '#F2CEEF', 'border': 1
                })
                cell_format = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'border': 1})
                for col_num, value in enumerate(export_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    for row_num, val in enumerate(export_df[value], start=1):
                        worksheet.write(row_num, col_num, val, cell_format)
                    max_len = max(export_df[value].astype(str).map(len).max(), len(value)) + 2
                    worksheet.set_column(col_num, col_num, max_len)
                worksheet.set_row(0, 35)
                for row in range(1, len(export_df)+1):
                    worksheet.set_row(row, 32)
            st.download_button(
                "Télécharger la répartition Excel",
                data=output_excel.getvalue(),
                file_name="repartition.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # --- PDF ---
        with col_pdf:
            output_pdf = io.BytesIO()
            doc = SimpleDocTemplate(output_pdf, pagesize=A4)
            elements = []
            data = [export_df.columns.tolist()] + export_df.values.tolist()
            table = Table(data, colWidths=[150, 100, 250])
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F2CEEF')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,0), (-1,0), 8),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('TOPPADDING', (0,1), (-1,-1), 12),
                ('BOTTOMPADDING', (0,1), (-1,-1), 12),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ])
            table.setStyle(style)
            elements.append(table)
            doc.build(elements)
            st.download_button(
                "Télécharger la répartition PDF",
                data=output_pdf.getvalue(),
                file_name="repartition.pdf",
                mime="application/pdf"
            )
