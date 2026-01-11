import streamlit as st
import pandas as pd
import random
import re
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# =============================
# SESSION STATE (OBLIGATOIRE)
# =============================
if "repartition" not in st.session_state:
    st.session_state.repartition = None

if "compteur" not in st.session_state:
    st.session_state.compteur = None

if "output_excel" not in st.session_state:
    st.session_state.output_excel = None

if "output_pdf" not in st.session_state:
    st.session_state.output_pdf = None

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Répartition bénévoles", layout="wide")
st.title("Répartition des mini-bénévoles")

# =============================
# SAISIE MANUELLE
# =============================
st.subheader("Saisie des créneaux")

data = st.data_editor(
    pd.DataFrame(
        columns=["DATE", "HORAIRES", "NOMS DES MINI-BÉNÉVOLES"]
    ),
    num_rows="dynamic",
    use_container_width=True
)

# =============================
# VALIDATION
# =============================
def validate(df):
    errors = []

    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    horaire_pattern = re.compile(r"^(10h|15h)$")
    noms_pattern = re.compile(r"^[^;]+(;[^;]+)*$")

    for i, r in df.iterrows():
        if not date_pattern.match(str(r["DATE"])):
            errors.append(f"Ligne {i+1} : date invalide")
        if not horaire_pattern.match(str(r["HORAIRES"])):
            errors.append(f"Ligne {i+1} : horaire invalide")
        if not noms_pattern.match(str(r["NOMS DES MINI-BÉNÉVOLES"])):
            errors.append(f"Ligne {i+1} : noms invalides (séparés par ;)")

    return errors

# =============================
# RÉPARTITION
# =============================
def repartir(df):
    rows = []
    compteur = {}

    for _, r in df.iterrows():
        noms = [n.strip() for n in r["NOMS DES MINI-BÉNÉVOLES"].split(";")]
        random.shuffle(noms)

        noms_affiches = ", ".join(noms)

        for n in noms:
            compteur[n] = compteur.get(n, 0) + 1

        horaire = "10h - 11h" if r["HORAIRES"] == "10h" else "15h - 16h"

        rows.append([
            r["DATE"],
            horaire,
            noms_affiches
        ])

    return rows, compteur

# =============================
# BOUTONS
# =============================
col1, col2 = st.columns(2)

with col1:
    lancer = st.button("Lancer la répartition")

with col2:
    relancer = st.button("Relancer avec un autre tirage")

if lancer or relancer:
    errors = validate(data)

    if errors:
        for e in errors:
            st.error(e)
    else:
        repartition, compteur = repartir(data)
        st.session_state.repartition = repartition
        st.session_state.compteur = compteur

# =============================
# AFFICHAGE
# =============================
if st.session_state.repartition is not None:
    st.subheader("Répartition")

    df_out = pd.DataFrame(
        st.session_state.repartition,
        columns=["DATE", "HORAIRES", "NOMS DES MINI-BÉNÉVOLES"]
    )

    st.dataframe(df_out, use_container_width=True)

    st.subheader("Occurrences par bénévole")
    st.write(
        pd.DataFrame(
            st.session_state.compteur.items(),
            columns=["Nom", "Occurrences"]
        )
    )

    # =============================
    # EXCEL
    # =============================
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Répartition")
        wb = writer.book
        ws = writer.sheets["Répartition"]

        header_format = wb.add_format({
            "bold": True,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#F2CEEF"
        })

        cell_format = wb.add_format({
            "border": 1,
            "valign": "vcenter"
        })

        for col in range(3):
            ws.write(0, col, df_out.columns[col], header_format)
            ws.set_column(col, col, 30)

        for row in range(1, len(df_out) + 1):
            ws.set_row(row, 30)
            for col in range(3):
                ws.write(row, col, df_out.iloc[row-1, col], cell_format)

        ws.set_row(0, 35)

    st.session_state.output_excel = excel_buffer.getvalue()

    # =============================
    # PDF
    # =============================
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)

    page_width, page_height = A4
    available_height = page_height - 100
    row_height = available_height / (len(df_out) + 1)

    table_data = [df_out.columns.tolist()] + df_out.values.tolist()

    table = Table(
        table_data,
        colWidths=[page_width / 3.2] * 3,
        rowHeights=[row_height] * len(table_data)
    )

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F2CEEF")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ]))

    doc.build([table])
    st.session_state.output_pdf = pdf_buffer.getvalue()

    # =============================
    # TÉLÉCHARGEMENTS
    # =============================
    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "Télécharger en Excel",
            st.session_state.output_excel,
            file_name="repartition.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with c2:
        st.download_button(
            "Télécharger en PDF",
            st.session_state.output_pdf,
            file_name="repartition.pdf",
            mime="application/pdf"
        )
