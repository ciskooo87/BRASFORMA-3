# ============================================================
# DASHBOARD COMERCIAL BRASFORMA – VERSÃO FINAL CORPORATIVA
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ============================================================
# CONFIGURAÇÃO INICIAL
# ============================================================
st.set_page_config(
    page_title="Brasforma – Dashboard Comercial",
    layout="wide",
)

# LOGO
try:
    st.sidebar.image("logo_brasforma.png", use_container_width=True)
except:
    pass

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def to_num(x):
    if pd.isna(x): 
        return np.nan
    if isinstance(x, (int, float)): 
        return float(x)
    s = str(x).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return np.nan


# ============================================================
# PIPELINE OFICIAL – BRASFORMA
# ============================================================

@st.cache_data
def load_brasforma(path: str, sheet="BD DASH"):
    df = pd.read_excel(path, sheet_name=sheet)
    df.columns = [c.strip() for c in df.columns]

    # Datas
    date_cols = [
        "Data / Mês","Data Final","Data do Pedido",
        "Data da Entrega","Data Inserção"
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numéricos base
    numeric_base = ["Valor Pedido R$", "Custo", "Quant. Pedidos"]
    for col in numeric_base:
        if col in df.columns:
            df[col] = df[col].apply(to_num)

    # Impostos
    impostos_cols = [
        "cofins","pis","ipi","icms","ipiReturned-T","icmsSt",
        "ipi-T","aproxtribFed","aproxtribState","cofinsDeson",
        "pisDeson","icmsDeson","icmsStFCP","icmsDifaRemet",
        "icmsDifaDest","icmsDifaFCP"
    ]

    for col in impostos_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].apply(to_num)

    df["Imposto Total"] = df[impostos_cols].sum(axis=1)

    # Faturamento Líquido
    df["Faturamento Líquido"] = df["Valor Pedido R$"] - df["Imposto Total"]

    # Custo Total
    df["Custo Total"] = df["Custo"] * df["Quant. Pedidos"]

    # Lucro Bruto
    df["Lucro Bruto"] = df["Valor Pedido R$"] - df["Custo Total"]

    df["Margem %"] = np.where(
        df["Valor Pedido R$"] > 0,
        100 * df["Lucro Bruto"] / df["Valor Pedido R$"],
        np.nan
    )

    # Ano / Mês
    df["Ano"] = df["Data / Mês"].dt.year
    df["Mes"] = df["Data / Mês"].dt.month
    df["Ano-Mes"] = df["Data / Mês"].dt.to_period("M").astype(str)

    # Lead Time
    df["LeadTime (dias)"] = (
        df["Data da Entrega"] - df["Data do Pedido"]
    ).dt.days

    # Atraso
    df["AtrasadoFlag"] = df["Atrasado / No prazo"].astype(str).str.contains(
        "Atr", case=False, na=False
    )

    # Chave Única
    df["PedidoItemKey"] = df["Pedido"].astype(str) + "-" + df["ITEM"].astype(str)

    return df


# ============================================================
# CARREGAR BASE
# ============================================================

df = load_brasforma("Dashboard - Comite Semanal - Brasforma IA (1).xlsx")

# ============================================================
# SIDEBAR – FILTROS
# ============================================================

st.sidebar.header("Filtros")

# Período
min_d = df["Data / Mês"].min()
max_d = df["Data / Mês"].max()

periodo = st.sidebar.date_input(
    "Período",
    value=(min_d, max_d),
    min_value=min_d,
    max_value=max_d,
)

df_f = df.copy()
df_f = df_f[
    (df_f["Data / Mês"] >= pd.to_datetime(periodo[0])) &
    (df_f["Data / Mês"] <= pd.to_datetime(periodo[1]))
]

# Representante
reps = st.sidebar.multiselect(
    "Representante", sorted(df["Representante"].dropna().unique())
)
if reps:
    df_f = df_f[df_f["Representante"].isin(reps)]

# UF
ufs = st.sidebar.multiselect(
    "UF", sorted(df["UF"].dropna().unique())
)
if ufs:
    df_f = df_f[df_f["UF"].isin(ufs)]

# Transação
trans = st.sidebar.multiselect(
    "TRANSAÇÃO", sorted(df["TRANSAÇÃO"].dropna().unique())
)
if trans:
    df_f = df_f[df_f["TRANSAÇÃO"].isin(trans)]

# Cliente
clientes = st.sidebar.multiselect(
    "Cliente", sorted(df["Nome Cliente"].dropna().unique())
)
if clientes:
    df_f = df_f[df_f["Nome Cliente"].isin(clientes)]


# ============================================================
# KPIS EXECUTIVOS
# ============================================================

st.title("📊 Dashboard Comercial Integrado – Brasforma")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Faturamento Líquido", f"R$ {df_f['Faturamento Líquido'].sum():,.2f}")
c2.metric("Faturamento Bruto", f"R$ {df_f['Valor Pedido R$'].sum():,.2f}")
c3.metric("Impostos", f"R$ {df_f['Imposto Total'].sum():,.2f}")
c4.metric("Pedidos", df_f["Pedido"].nunique())

# ============================================================
# GRÁFICOS TEMPORAIS
# ============================================================

st.header("📈 Evolução Mensal")

dfm = df_f.groupby("Ano-Mes", as_index=False).agg(
    FatLiq=("Faturamento Líquido", "sum"),
    FatBruto=("Valor Pedido R$", "sum"),
    Impostos=("Imposto Total", "sum")
)

fig = px.line(dfm, x="Ano-Mes", y="FatLiq", markers=True, title="Faturamento Líquido")
st.plotly_chart(fig, use_container_width=True)

fig2 = px.bar(dfm, x="Ano-Mes", y="Impostos", title="Impostos por Mês")
st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# ABAS DE ANÁLISE
# ============================================================

st.header("🔍 Análises Detalhadas")

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "Clientes",
    "Representantes",
    "UF / Geografia",
    "Produtos / Rentabilidade",
    "Atrasos e Lead Time"
])

with aba1:
    st.subheader("Ranking de Clientes")
    cli = df_f.groupby("Nome Cliente", as_index=False).agg(
        FatLiq=("Faturamento Líquido","sum"),
        Pedidos=("Pedido","nunique")
    )
    st.dataframe(cli.sort_values("FatLiq", ascending=False))

with aba2:
    st.subheader("Performance por Representante")
    rep = df_f.groupby("Representante", as_index=False).agg(
        FatLiq=("Faturamento Líquido","sum"),
        FatBruto=("Valor Pedido R$","sum"),
        Impostos=("Imposto Total","sum"),
        Lucro=("Lucro Bruto","sum")
    )
    st.dataframe(rep.sort_values("FatLiq", ascending=False))

with aba3:
    st.subheader("Faturamento por UF")
    geo = df_f.groupby("UF", as_index=False).agg(
        FatLiq=("Faturamento Líquido","sum"),
        Pedidos=("Pedido","nunique")
    )
    st.dataframe(geo.sort_values("FatLiq", ascending=False))

with aba4:
    st.subheader("Rentabilidade por ITEM")
    sku = df_f.groupby("ITEM", as_index=False).agg(
        FatLiq=("Faturamento Líquido","sum"),
        Custo=("Custo Total","sum"),
        Lucro=("Lucro Bruto","sum"),
        Qtd=("Quant. Pedidos","sum"),
    )
    st.dataframe(sku.sort_values("FatLiq", ascending=False))

with aba5:
    st.subheader("Análise de Atrasos")
    atrasos = df_f.groupby("AtrasadoFlag", as_index=False).agg(
        Pedidos=("Pedido","nunique")
    )
    st.dataframe(atrasos)


# ============================================================
# RODAPÉ
# ============================================================

st.markdown("---")
st.caption("Powered by Brasforma • Arquitetura Comercial Inteligente • IA aplicada a dados corporativos.")
