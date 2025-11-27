# ============================================================
#   DASHBOARD COMERCIAL BRASFORMA – NOVA VERSÃO DO ZERO
#   Layout: PROFISSIONAL
#   Estrutura limpa, estável, corporativa
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path

# ------------------------------------------------------------
# CONFIGURAÇÃO DO APP
# ------------------------------------------------------------
st.set_page_config(
    page_title="Brasforma – Dashboard Comercial",
    layout="wide"
)

# Logo na sidebar
try:
    st.sidebar.image("logo_brasforma.png", use_container_width=True)
except FileNotFoundError:
    st.sidebar.info("Envie o arquivo logo_brasforma.png para exibir o logotipo.")

# ------------------------------------------------------------
# FUNÇÕES UTILITÁRIAS
# ------------------------------------------------------------
def to_num(x):
    """Converte valores da base para número, com tolerância a vírgulas e pontos."""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    x = str(x).replace(".", "").replace(",", ".")
    try:
        return float(x)
    except:
        return np.nan

def fmt_money(v):
    if pd.isna(v):
        return "-"
    return ("R$ " + f"{v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_int(v):
    if pd.isna(v):
        return "-"
    return f"{int(v):,}".replace(",", ".")

def fmt_pct(v):
    if pd.isna(v):
        return "-"
    return f"{v:.1f}%".replace(".", ",")

# ------------------------------------------------------------
# LEITURA DA BASE – ABA ÚNICA: BD DASH
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_base(path="Dashboard - Comite Semanal - Brasforma IA (1).xlsx"):
    """Carrega e padroniza a base principal.

    O retorno é um DataFrame já com conversões numéricas, datas e campos
    derivados para facilitar as demais análises.
    """

    file_path = Path(path)
    if not file_path.exists():
        st.error(
            "Arquivo de base não encontrado. Envie o Excel na raiz do projeto ou "
            "atualize o parâmetro 'path'."
        )
        return pd.DataFrame()

    df = pd.read_excel(file_path, sheet_name="BD DASH")
    df.columns = [c.strip() for c in df.columns]

    # Conversões numéricas
    num_cols = [
        "Valor Pedido R$", "Custo", "Quant. Pedidos",
        "cofins","pis","ipi","icms","ipiReturned-T","icmsSt","ipi-T",
        "aproxtribFed","aproxtribState","cofinsDeson","pisDeson","icmsDeson",
        "icmsStFCP","icmsDifaRemet","icmsDifaDest","icmsDifaFCP"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = df[c].apply(to_num)

    # Datas
    date_cols = [
        "Data / Mês","Data Final","Data do Pedido",
        "Data da Entrega","Data Inserção"
    ]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Imposto Total
    imposto_cols = [
        "cofins","pis","ipi","icms","ipiReturned-T","icmsSt","ipi-T",
        "aproxtribFed","aproxtribState","cofinsDeson","pisDeson","icmsDeson",
        "icmsStFCP","icmsDifaRemet","icmsDifaDest","icmsDifaFCP"
    ]
    df["Imposto Total"] = df[imposto_cols].sum(axis=1)

    # Faturamentos
    df["Faturamento Bruto"] = df["Valor Pedido R$"]
    df["Faturamento Líquido"] = df["Valor Pedido R$"] - df["Imposto Total"]

    # Custo Total
    df["Custo Total"] = df["Custo"] * df["Quant. Pedidos"]

    # Lucros e Margens
    df["Lucro Bruto"] = df["Faturamento Bruto"] - df["Custo Total"]
    df["Margem Bruta %"] = np.where(
        df["Faturamento Bruto"] > 0,
        100 * df["Lucro Bruto"] / df["Faturamento Bruto"],
        np.nan
    )

    df["Lucro Líquido"] = df["Faturamento Líquido"] - df["Custo Total"]
    df["Margem Líquida %"] = np.where(
        df["Faturamento Líquido"] > 0,
        100 * df["Lucro Líquido"] / df["Faturamento Líquido"],
        np.nan
    )

    # Derivações de data
    df["Ano"] = df["Data / Mês"].dt.year
    df["Mes"] = df["Data / Mês"].dt.month
    df["Ano-Mes"] = df["Data / Mês"].dt.to_period("M").astype(str)

    # Lead time
    df["Lead Time (dias)"] = (df["Data da Entrega"] - df["Data do Pedido"]).dt.days

    # Flag atraso
    df["AtrasadoFlag"] = df["Atrasado / No prazo"].astype(str).str.contains("Atras", case=False, na=False)

    return df
# ============================================================
#   BLOCO 2 — SIDEBAR: FILTROS GLOBAIS + NAVEGAÇÃO
# ============================================================

# Carregar base
df = load_base()
if df.empty:
    st.stop()

st.sidebar.title("Navegação")

# -------------------------------
# MENU LATERAL – PÁGINAS
# -------------------------------
menu = st.sidebar.radio(
    "Selecione a página:",
    [
        "Visão Executiva",
        "Visão Temporal",
        "Clientes – Ranking & Análises",
        "Representantes – Performance",
        "Produtos – Rentabilidade",
        "Geografia – UF / Região",
        "Impostos",
        "Rentabilidade Bruto → Líquido",
        "ABC / Pareto",
        "RFM – Recência / Frequência / Monetário",
        "Operacional – Lead Time / Atrasos",
        "Simulador Comercial",
        "Exportações"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Filtros Globais")

# -------------------------------
# FILTRO — PERÍODO
# -------------------------------
min_date = df["Data / Mês"].min()
max_date = df["Data / Mês"].max()

date_range = st.sidebar.date_input(
    "Período",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    df_f = df[(df["Data / Mês"] >= pd.to_datetime(start)) &
              (df["Data / Mês"] <= pd.to_datetime(end))]
else:
    df_f = df.copy()

# -------------------------------
# FILTRO — REPRESENTANTE
# -------------------------------
if "Representante" in df.columns:
    reps = st.sidebar.multiselect(
        "Representante",
        sorted(df["Representante"].dropna().unique())
    )
    if reps:
        df_f = df_f[df_f["Representante"].isin(reps)]

# -------------------------------
# FILTRO — CLIENTE
# -------------------------------
if "Nome Cliente" in df.columns:
    clientes = st.sidebar.multiselect(
        "Cliente",
        sorted(df["Nome Cliente"].dropna().unique())
    )
    if clientes:
        df_f = df_f[df_f["Nome Cliente"].isin(clientes)]

# -------------------------------
# FILTRO — UF
# -------------------------------
if "UF" in df.columns:
    ufs = st.sidebar.multiselect(
        "UF",
        sorted(df["UF"].dropna().unique())
    )
    if ufs:
        df_f = df_f[df_f["UF"].isin(ufs)]

# -------------------------------
# FILTRO — ITEM / SKU
# -------------------------------
if "ITEM" in df.columns:
    skus = st.sidebar.multiselect(
        "SKU (ITEM)",
        sorted(df["ITEM"].dropna().unique())
    )
    if skus:
        df_f = df_f[df_f["ITEM"].isin(skus)]

# -------------------------------
# FILTRO — TRANSAÇÃO
# -------------------------------
if "TRANSAÇÃO" in df.columns:
    trans = st.sidebar.multiselect(
        "Transação",
        sorted(df["TRANSAÇÃO"].dropna().unique())
    )
    if trans:
        df_f = df_f[df_f["TRANSAÇÃO"].isin(trans)]

# -------------------------------
# FILTRO — REGIONAL
# -------------------------------
if "Regional" in df.columns:
    regs = st.sidebar.multiselect(
        "Regional",
        sorted(df["Regional"].dropna().unique())
    )
    if regs:
        df_f = df_f[df_f["Regional"].isin(regs)]

# -------------------------------
# FILTRO — STATUS
# -------------------------------
if "Status de Produção / Faturamento" in df.columns:
    stats = st.sidebar.multiselect(
        "Status Produção / Faturamento",
        sorted(df["Status de Produção / Faturamento"].dropna().unique())
    )
    if stats:
        df_f = df_f[df_f["Status de Produção / Faturamento"].isin(stats)]

# -------------------------------
# FILTRO — SEMANA
# -------------------------------
if "Semana" in df.columns:
    semanas = st.sidebar.multiselect(
        "Semana",
        sorted(df["Semana"].dropna().unique())
    )
    if semanas:
        df_f = df_f[df_f["Semana"].isin(semanas)]

# -------------------------------
# BASE FILTRADA EM MÃOS
# -------------------------------
# ============================================================
#   BLOCO 3 — VISÃO EXECUTIVA
# ============================================================

def page_visao_executiva(df_f):

    st.header("📌 Visão Executiva – Painel Comercial Brasforma")

    df_f = df_f.copy()

    if df_f.empty:
        st.warning("Não há dados para os filtros selecionados.")
        return

    # -------------------------------
    # MÉTRICAS-CHAVE
    # -------------------------------

    fat_bruto = df_f["Valor Pedido R$"].sum()
    imp_total = df_f["Imposto Total"].sum()
    fat_liquido = df_f["Faturamento Líquido"].sum()
    custo_total = df_f["Custo Total"].sum()
    pedidos = df_f["Pedido"].nunique()
    qtd_total = df_f["Quant. Pedidos"].sum()

    lucro_bruto = fat_bruto - custo_total
    margem_bruta_pct = (lucro_bruto / fat_bruto * 100) if fat_bruto > 0 else 0

    ticket_medio = (fat_bruto / pedidos) if pedidos > 0 else 0

    # -------------------------------
    # EXIBIÇÃO DOS KPIs
    # -------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento Bruto", f"R$ {fat_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Faturamento Líquido", f"R$ {fat_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Impostos Totais", f"R$ {imp_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c4.metric("Pedidos", f"{pedidos:,}".replace(",", "."))

    c5, c6, c7 = st.columns(3)
    c5.metric("Custo Total", f"R$ {custo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c6.metric("Margem Bruta (%)", f"{margem_bruta_pct:.1f}%".replace(".", ","))
    c7.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # -------------------------------
    # RESUMO FINANCEIRO EXPANDIDO
    # -------------------------------
    st.subheader("Resumo Financeiro Completo")

    resumo = pd.DataFrame({
        "Indicador": [
            "Faturamento Bruto",
            "Impostos Totais",
            "Faturamento Líquido",
            "Custo Total",
            "Lucro Bruto",
            "Margem Bruta (%)",
            "Pedidos",
            "Qtd Total Vendida",
            "Ticket Médio"
        ],
        "Valor": [
            fat_bruto,
            imp_total,
            fat_liquido,
            custo_total,
            lucro_bruto,
            margem_bruta_pct,
            pedidos,
            qtd_total,
            ticket_medio
        ]
    })

    st.dataframe(resumo, use_container_width=True)
# ============================================================
#   BLOCO 4 — VISÃO TEMPORAL (EVOLUÇÃO)
# ============================================================

def page_visao_temporal(df_f):

    st.header("📈 Evolução Temporal – Faturamento, Impostos e Volume")

    df_f = df_f.copy()

    if df_f.empty:
        st.warning("Não há dados para os filtros aplicados.")
        return

    # ---------------------------------
    # Preparar base
    # ---------------------------------
    df_f["Ano-Mes"] = df_f["Data / Mês"].dt.to_period("M").astype(str)

    base = df_f.groupby("Ano-Mes", as_index=False).agg(
        FatBruto=("Valor Pedido R$", "sum"),
        FatLiquido=("Faturamento Líquido", "sum"),
        Impostos=("Imposto Total", "sum"),
        Qtd=("Quant. Pedidos", "sum")
    )

    # ---------------------------------
    # Gráfico 1 — Faturamento Bruto vs Líquido
    # ---------------------------------
    st.subheader("Faturamento Bruto x Líquido")

    chart_fat = alt.Chart(base).mark_line(point=True).encode(
        x=alt.X("Ano-Mes:O", title="Ano-Mês"),
        y=alt.Y("FatBruto:Q", title="Faturamento Bruto"),
        tooltip=["Ano-Mes", "FatBruto", "FatLiquido"]
    ).properties(height=350).interactive()

    chart_fat_liq = alt.Chart(base).mark_line(point=True, color="green").encode(
        x="Ano-Mes:O",
        y="FatLiquido:Q",
        tooltip=["Ano-Mes", "FatLiquido"]
    )

    st.altair_chart(chart_fat + chart_fat_liq, use_container_width=True)

    st.markdown("---")

    # ---------------------------------
    # Gráfico 2 — Impostos Mensais
    # ---------------------------------
    st.subheader("Impostos Totais por Mês")

    chart_imp = alt.Chart(base).mark_bar(color="#d95f02").encode(
        x="Ano-Mes:O",
        y="Impostos:Q",
        tooltip=["Ano-Mes", "Impostos"]
    ).properties(height=300).interactive()

    st.altair_chart(chart_imp, use_container_width=True)

    st.markdown("---")

    # ---------------------------------
    # Gráfico 3 — Volume (Qtd Pedida)
    # ---------------------------------
    st.subheader("Volume Vendido (Quantidade de Itens)")

    chart_qtd = alt.Chart(base).mark_line(point=True, color="#1b9e77").encode(
        x="Ano-Mes:O",
        y="Qtd:Q",
        tooltip=["Ano-Mes", "Qtd"]
    ).properties(height=300).interactive()

    st.altair_chart(chart_qtd, use_container_width=True)
# ============================================================
#   BLOCO 5 — CLIENTES (RANKING + ANÁLISES)
# ============================================================

def page_clientes(df_f):

    st.header("👥 Análises de Clientes – Ranking & Indicadores")

    df_f = df_f.copy()

    if df_f.empty:
        st.warning("Nenhum dado encontrado para os filtros aplicados.")
        return

    # ---------------------------------
    # AGRUPAMENTO POR CLIENTE
    # ---------------------------------
    cli = df_f.groupby("Nome Cliente", as_index=False).agg(
        FatBruto=("Valor Pedido R$", "sum"),
        FatLiquido=("Faturamento Líquido", "sum"),
        Impostos=("Imposto Total", "sum"),
        Custo=("Custo Total", "sum"),
        Qtd=("Quant. Pedidos", "sum"),
        Pedidos=("Pedido", "nunique")
    )

    cli["Lucro Bruto"] = cli["FatBruto"] - cli["Custo"]
    cli["Margem Bruta %"] = np.where(
        cli["FatBruto"] > 0,
        100 * cli["Lucro Bruto"] / cli["FatBruto"],
        np.nan
    )

    cli["Ticket Médio"] = cli["FatBruto"] / cli["Pedidos"]

    # ---------------------------------
    # RANKINGS
    # ---------------------------------
    st.subheader("🏆 Ranking de Clientes por Faturamento")

    top_fat = cli.sort_values("FatBruto", ascending=False).head(20)

    st.dataframe(
        top_fat,
        use_container_width=True
    )

    st.markdown("---")

    # ---------------------------------
    # GRÁFICO: TOP 20 CLIENTES
    # ---------------------------------
    st.subheader("📊 Top 20 Clientes – Faturamento Bruto")

    chart_top = alt.Chart(top_fat).mark_bar().encode(
        x=alt.X("FatBruto:Q", title="Faturamento"),
        y=alt.Y("Nome Cliente:N", sort="-x"),
        tooltip=["Nome Cliente", "FatBruto", "FatLiquido", "Impostos", "Lucro Bruto", "Margem Bruta %"]
    ).properties(height=600)

    st.altair_chart(chart_top, use_container_width=True)

    st.markdown("---")

    # ---------------------------------
    # ANÁLISES ADICIONAIS
    # ---------------------------------
    st.subheader("📌 Indicadores Gerais dos Clientes")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    kpi1.metric("Total de Clientes Ativos", f"{cli.shape[0]:,}".replace(",", "."))
    kpi2.metric("Ticket Médio Geral", f"R$ {cli['FatBruto'].sum() / cli['Pedidos'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    kpi3.metric("Média de Margem (%)", f"{cli['Margem Bruta %'].mean():.1f}%".replace(".", ","))
    kpi4.metric("Imposto Médio por Cliente", f"R$ {cli['Impostos'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # ---------------------------------
    # TABELA COMPLETA
    # ---------------------------------
    st.subheader("📋 Tabela Completa de Clientes")

    st.dataframe(
        cli.sort_values("FatBruto", ascending=False),
        use_container_width=True
    )
# ============================================================
#   BLOCO 6 — REPRESENTANTES (PERFORMANCE COMERCIAL)
# ============================================================

def page_representantes(df_f):

    st.header("🧑‍💼 Performance dos Representantes – Faturamento, Margem e Impostos")

    df_f = df_f.copy()

    if df_f.empty:
        st.warning("Nenhum dado encontrado para os filtros aplicados.")
        return

    # ---------------------------------
    # AGRUPAMENTO POR REPRESENTANTE
    # ---------------------------------
    rep = df_f.groupby("Representante", as_index=False).agg(
        FatBruto=("Valor Pedido R$", "sum"),
        FatLiquido=("Faturamento Líquido", "sum"),
        Impostos=("Imposto Total", "sum"),
        Custo=("Custo Total", "sum"),
        Pedidos=("Pedido", "nunique"),
        Qtd=("Quant. Pedidos", "sum"),
    )

    rep["Lucro Bruto"] = rep["FatBruto"] - rep["Custo"]

    rep["Margem Bruta %"] = np.where(
        rep["FatBruto"] > 0,
        100 * rep["Lucro Bruto"] / rep["FatBruto"],
        np.nan
    )

    rep["Ticket Médio"] = rep["FatBruto"] / rep["Pedidos"]

    # ---------------------------------
    # KPIs GERAIS
    # ---------------------------------
    st.subheader("📌 Indicadores Gerais da Força de Vendas")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Qtd Representantes Ativos", f"{rep.shape[0]:,}".replace(",", "."))
    col2.metric(
        "Ticket Médio Geral", 
        "R$ " + f"{rep['Ticket Médio'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    col3.metric(
        "Margem Média (%)", 
        f"{rep['Margem Bruta %'].mean():.1f}%".replace(".", ",")
    )
    col4.metric(
        "Imposto Médio",
        "R$ " + f"{rep['Impostos'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    st.markdown("---")

    # ---------------------------------
    # RANKING
    # ---------------------------------
    st.subheader("🏆 Ranking de Representantes por Faturamento")

    top_rep = rep.sort_values("FatBruto", ascending=False)

    st.dataframe(top_rep, use_container_width=True)

    st.markdown("---")

    # ---------------------------------
    # GRÁFICO: Faturamento Líquido
    # ---------------------------------
    st.subheader("📊 Faturamento Líquido por Representante")

    chart_rep = alt.Chart(top_rep).mark_bar().encode(
        x=alt.X("FatLiquido:Q", title="Faturamento Líquido"),
        y=alt.Y("Representante:N", sort="-x"),
        tooltip=["Representante", "FatLiquido", "FatBruto", "Lucro Bruto", "Margem Bruta %", "Impostos"]
    ).properties(height=600)

    st.altair_chart(chart_rep, use_container_width=True)

    st.markdown("---")

    # ---------------------------------
    # TABELA COMPLETA
    # ---------------------------------
    st.subheader("📋 Tabela Completa de Representantes")

    st.dataframe(
        rep.sort_values("FatBruto", ascending=False),
        use_container_width=True
    )
# ============================================================
#   BLOCO 7 — GEOGRAFIA (UF, Região e Impacto Tributário)
# ============================================================

def page_geografia(df_f):

    st.header("🗺️ Análises Geográficas – UF e Regiões")

    df_f = df_f.copy()

    if df_f.empty:
        st.warning("Nenhum dado encontrado para os filtros aplicados.")
        return

    # ------------------------------------------------------------------------------------
    # AGRUPAMENTO UF
    # ------------------------------------------------------------------------------------
    uf = df_f.groupby("UF", as_index=False).agg(
        FatBruto=("Valor Pedido R$", "sum"),
        FatLiquido=("Faturamento Líquido", "sum"),
        Impostos=("Imposto Total", "sum"),
        Custo=("Custo Total", "sum"),
        Pedidos=("Pedido", "nunique"),
        Qtd=("Quant. Pedidos", "sum")
    )

    uf["Lucro Bruto"] = uf["FatBruto"] - uf["Custo"]

    uf["Margem Bruta %"] = np.where(
        uf["FatBruto"] > 0,
        100 * uf["Lucro Bruto"] / uf["FatBruto"],
        np.nan
    )

    uf["Ticket Médio"] = uf["FatBruto"] / uf["Pedidos"]

    # ------------------------------------------------------------------------------------
    # KPIs EXECUTIVOS
    # ------------------------------------------------------------------------------------
    st.subheader("📌 KPIs Geográficos")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("UFs Atendidas", uf.shape[0])
    c2.metric(
        "Ticket Médio Geral",
        "R$ " + f"{uf['Ticket Médio'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    c3.metric("Margem Média (%)", f"{uf['Margem Bruta %'].mean():.1f}%".replace(".", ","))
    c4.metric(
        "Imposto Médio por UF",
        "R$ " + f"{uf['Impostos'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    st.markdown("---")

    # ------------------------------------------------------------------------------------
    # RANKING POR UF
    # ------------------------------------------------------------------------------------
    st.subheader("🏆 Ranking por UF – Faturamento Bruto")

    st.dataframe(
        uf.sort_values("FatBruto", ascending=False),
        use_container_width=True
    )

    st.markdown("---")

    # ------------------------------------------------------------------------------------
    # GRÁFICO UF – FATURAMENTO LÍQUIDO
    # ------------------------------------------------------------------------------------
    st.subheader("📊 Faturamento Líquido por UF")

    chart_uf = alt.Chart(uf.sort_values("FatLiquido", ascending=False)).mark_bar().encode(
        x=alt.X("FatLiquido:Q", title="Faturamento Líquido"),
        y=alt.Y("UF:N", sort="-x"),
        tooltip=["UF", "FatLiquido", "FatBruto", "Impostos", "Lucro Bruto", "Margem Bruta %"]
    ).properties(height=600)

    st.altair_chart(chart_uf, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------------------------
    # IMPACTO TRIBUTÁRIO
    # ------------------------------------------------------------------------------------
    st.subheader("💸 Impacto Tributário por UF")

    uf["Peso Tributário %"] = np.where(
        uf["FatBruto"] > 0,
        100 * uf["Impostos"] / uf["FatBruto"],
        np.nan
    )

    chart_imp = alt.Chart(uf.sort_values("Peso Tributário %", ascending=False)).mark_bar(color="#cc4444").encode(
        x=alt.X("Peso Tributário %:Q", title="% do Faturamento Bruto"),
        y=alt.Y("UF:N", sort="-x"),
        tooltip=["UF", "Impostos", "FatBruto", "Peso Tributário %"]
    ).properties(height=550)

    st.altair_chart(chart_imp, use_container_width=True)

    st.markdown("---")

    # ------------------------------------------------------------------------------------
    # TABELA COMPLETA
    # ------------------------------------------------------------------------------------
    st.subheader("📋 Tabela Completa por UF")

    st.dataframe(
        uf.sort_values("FatBruto", ascending=False),
        use_container_width=True
    )
# ============================================================
#   BLOCO 8 — RFM + PARETO (CLIENTES)
# ============================================================

def page_rfm_pareto(df_f):

    st.header("📈 RFM & Pareto – Análise de Valor dos Clientes")

    df_f = df_f.copy()

    if df_f.empty:
        st.warning("Nenhum dado encontrado para os filtros aplicados.")
        return

    # ================================================================
    # RFM — RECÊNCIA, FREQUÊNCIA, MONETÁRIO
    # ================================================================
    st.subheader("🔎 Análise RFM")

    # Recência: dias desde o último pedido
    max_date = df_f["Data do Pedido"].max()
    df_f["Recencia"] = (max_date - df_f["Data do Pedido"]).dt.days

    rfm = df_f.groupby("Nome Cliente", as_index=False).agg(
        Recencia=("Recencia", "min"),
        Frequencia=("Pedido", "nunique"),
        Monetario=("Faturamento Líquido", "sum")
    )

    # Tabela RFM
    st.dataframe(
        rfm.sort_values("Monetario", ascending=False),
        use_container_width=True
    )

    # KPIs RFM
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    col1.metric("Recência Média (dias)", f"{rfm['Recencia'].mean():.1f}".replace(".", ","))
    col2.metric("Frequência Média", f"{rfm['Frequencia'].mean():.1f}".replace(".", ","))
    col3.metric("Valor Monetário Médio", "R$ " + f"{rfm['Monetario'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # ================================================================
    # GRÁFICO RFM – DISPERSÃO
    # ================================================================
    st.subheader("📊 Mapa de Dispersão – Frequência x Valor Monetário")

    chart_rfm = alt.Chart(rfm).mark_circle(size=140).encode(
        x=alt.X("Frequencia:Q", title="Frequência (Pedidos)"),
        y=alt.Y("Monetario:Q", title="Valor Monetário (Fat. Líquido)"),
        color=alt.Color("Recencia:Q", scale=alt.Scale(scheme="reds")),
        tooltip=["Nome Cliente", "Recencia", "Frequencia", "Monetario"]
    ).properties(height=500)

    st.altair_chart(chart_rfm, use_container_width=True)

    st.markdown("---")

    # ================================================================
    # PARETO — CURVA 80/20 DE FATURAMENTO
    # ================================================================
    st.subheader("🏆 Pareto 80/20 – Clientes que sustentam o negócio")

    pareto = df_f.groupby("Nome Cliente", as_index=False).agg(
        FatLiquido=("Faturamento Líquido", "sum")
    )

    pareto = pareto.sort_values("FatLiquido", ascending=False)
    pareto["% Linha"] = pareto["FatLiquido"] / pareto["FatLiquido"].sum() * 100
    pareto["% Acum"] = pareto["% Linha"].cumsum()

    # Gráfico Pareto
    chart_pareto = alt.Chart(pareto).mark_line(point=True).encode(
        x=alt.X("Nome Cliente:N", sort=None, title="Clientes"),
        y=alt.Y("% Acum:Q", title="% Acumulado do Faturamento"),
        tooltip=["Nome Cliente", "% Linha", "% Acum", "FatLiquido"]
    ).properties(height=400)

    st.altair_chart(chart_pareto, use_container_width=True)

    # Tabela Pareto
    st.dataframe(
        pareto,
        use_container_width=True
    )

    st.markdown("### 🎯 Interpretação rápida")
    st.write("""
        • Clientes até ~20% da lista acumulam cerca de 80% do faturamento.
        • Esses clientes são “core” e precisam de estratégia diferenciada.
        • Clientes abaixo de 5% do acumulado raro contribuem; podem ser oportunidades ou drenagem operacional.
    """)


def page_em_breve(titulo: str) -> None:
    """Placeholder para páginas ainda não implementadas."""

    st.header(titulo)
    st.info(
        "Esta seção ainda não possui visualizações disponíveis. "
        "Envie uma nova versão da base ou descreva as necessidades para priorizarmos a implementação."
    )


def main() -> None:
    """Roteia o menu lateral para a página correspondente."""

    df_filtrado = df_f.copy()

    pages = {
        "Visão Executiva": page_visao_executiva,
        "Visão Temporal": page_visao_temporal,
        "Clientes – Ranking & Análises": page_clientes,
        "Representantes – Performance": page_representantes,
        "Produtos – Rentabilidade": page_em_breve,
        "Geografia – UF / Região": page_geografia,
        "Impostos": page_em_breve,
        "Rentabilidade Bruto → Líquido": page_em_breve,
        "ABC / Pareto": page_em_breve,
        "RFM – Recência / Frequência / Monetário": page_rfm_pareto,
        "Operacional – Lead Time / Atrasos": page_em_breve,
        "Simulador Comercial": page_em_breve,
        "Exportações": page_em_breve,
    }

    page_fn = pages.get(menu, page_em_breve)

    if page_fn is page_em_breve:
        page_fn(menu)
    else:
        page_fn(df_filtrado)


if __name__ == "__main__":
    main()
