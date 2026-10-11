import streamlit as st
import bibtexparser
from bibtexparser.bparser import BibTexParser
import pandas as pd
from collections import Counter
import networkx as nx
from pyvis.network import Network
import tempfile
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

st.title("Análisis de archivo BibTeX")

uploaded_file = st.file_uploader("Sube tu archivo .bib", type=["bib"])

if uploaded_file is not None:
    st.success("Archivo cargado correctamente.")

    # Leer contenido
    content = uploaded_file.read().decode("utf-8")

    # Parsear con bibtexparser 1.4
    parser = BibTexParser(common_strings=True)
    bib_database = bibtexparser.loads(content, parser=parser)

    # Entradas como diccionarios reales
    entries = [entry for entry in bib_database.entries]

    st.subheader("Entradas encontradas")
    st.write(f"Total de entradas: {len(entries)}")
    st.dataframe(entries)

    # DataFrame
    df = pd.DataFrame(entries)

    st.subheader("Campos detectados")
    st.write(set(df.columns))

    st.subheader("Análisis básico")

    # ============================
    #        AUTORES
    # ============================

    df["author"] = df.get("author", None)

    def split_authors(a):
        if pd.isna(a):
            return []
        return [x.strip() for x in a.split(" and ")]

    df["authors_list"] = df["author"].apply(split_authors)

    author_counts = Counter([a for lst in df["authors_list"] for a in lst])

    st.write("Autores más frecuentes:")
    st.dataframe(pd.DataFrame(author_counts.items(), columns=["Autor", "Frecuencia"]))

    # ============================
    #        AÑOS
    # ============================

    df["year"] = pd.to_numeric(df.get("year", None), errors="coerce")
    st.write("Distribución por año:")
    st.bar_chart(df["year"].value_counts().sort_index())

    # ============================
    #     PALABRAS CLAVE
    # ============================

    df["keywords"] = df.get("keywords", None)

    def split_keywords(k):
        if pd.isna(k):
            return []
        return [x.strip() for x in k.split(",")]

    df["keywords_list"] = df["keywords"].apply(split_keywords)

    keyword_counts = Counter([k for lst in df["keywords_list"] for k in lst])

    st.write("Palabras clave más frecuentes:")
    st.dataframe(pd.DataFrame(keyword_counts.items(), columns=["Keyword", "Frecuencia"]))

    # ============================
    #     RED AUTOR–TEMA (BIPARTITA)
    # ============================

    st.subheader("Mapa discursivo: Red Autor–Tema")

    # Crear grafo bipartito
    G = nx.Graph()

    for authors, keywords in zip(df["authors_list"], df["keywords_list"]):
        for a in authors:
            G.add_node(a, type="author")
        for k in keywords:
            G.add_node(k, type="keyword")

        for a in authors:
            for k in keywords:
                if G.has_edge(a, k):
                    G[a][k]["weight"] += 1
                else:
                    G.add_edge(a, k, weight=1)

    # Visualización interactiva con PyVis
    net = Network(height="900px", width="100%", bgcolor="#111111", font_color="white")
    net.force_atlas_2based()

    for node, data in G.nodes(data=True):
        if data["type"] == "author":
            net.add_node(node, label=node, color="#1f77b4", size=25)
        else:
            net.add_node(node, label=node, color="#ff7f0e", size=20)

    for source, target, data in G.edges(data=True):
        net.add_edge(source, target, value=data["weight"])

    # Guardar HTML temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        html_path = Path(tmp_file.name)

    # Mostrar en Streamlit (nuevo método)
    st.iframe(html_path, height=900)

    # Guardar HTML permanente
    net.save_graph("mapa_discursivo.html")

    st.success("Mapa discursivo exportado como HTML. Ábrelo en tu navegador para verlo en pantalla completa.")
    st.download_button(
        label="Descargar HTML del mapa",
        data=open("mapa_discursivo.html", "rb"),
        file_name="mapa_discursivo.html",
        mime="text/html"
    )

