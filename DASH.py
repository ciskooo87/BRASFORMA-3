# ============================================================
# DASHBOARD COMERCIAL BRASFORMA – VERSÃO FINAL CORPORATIVA
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ===========================================================
# FORMATAÇÃO GLOBAL PADRONIZADA – válido para o dashboard inteiro
# ===========================================================

def fmt_money(v):
    try:
        if pd.isna(v): return "-"
        return "R$ {:,.2f}".format(float(v)).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "-"

def fmt_pct(v, decimals=1):
    try:
        if pd.isna(v): return "-"
        return f"{float(v):.{decimals}f}%".replace(".", ",")
    except:
        return "-"

def fmt_int(v):
    try:
        if pd.isna(v): return "-"
        return "{:,.0f}".format(float(v)).replace(",", ".")
    except:
        return "-"

def apply_global_formatting(df):
    """
    Formatação automática baseada em palavras-chave do nome da coluna.
    Funciona para 100% das abas sem manutenção manual.
    """

    df2 = df.copy()

    money_keywords = ["valor", "fat", "preço", "custo", "imposto", "receita", "total", "ticket"]
    pct_keywords = ["marg", "perc", "%"]
    int_keywords = ["qtd", "quant", "pedido", "itens", "freq", "clientesativos"]

    for col in df2.columns:
        col_lower = col.lower()

        if any(k in col_lower for k in money_keywords):
            df2[col] = df2[col].apply(fmt_money)

        elif any(k in col_lower for k in pct_keywords):
            df2[col] = df2[col].apply(fmt_pct)

        elif any(k in col_lower for k in int_keywords):
            df2[col] = df2[col].apply(fmt_int)

    return df2


def format_dataframe(df, money_cols=None, pct_cols=None, int_cols=None):
    """
    Formatação manual quando você precisa “forçar” alguma coluna específica.
    """
    df2 = df.copy()
    money_cols = money_cols or []
    pct_cols = pct_cols or []
    int_cols = int_cols or []

    for col in df2.columns:
        if col in money_cols:
            df2[col] = df2[col].apply(fmt_money)
        elif col in pct_cols:
            df2[col] = df2[col].apply(fmt_pct)
        elif col in int_cols:
            df2[col] = df2[col].apply(fmt_int)

    return df2


from inteligencia_comercial import (
    clientes_em_crescimento,
    clientes_em_queda,
    skus_em_tendencia,
    cesta_por_regiao,
    detectar_anomalias
)


# ============================================================
# CONFIGURAÇÃO INICIAL
# ============================================================
st.set_page_config(
    page_title="Brasforma – Dashboard Comercial",
    layout="wide",
)
st.markdown("""
<style>

    /* reduz topo do app */
    .block-container {
        padding-top: 1.2rem;
    }

    /* cartões executivos */
    .metric-card {
        background-color: #111111;
        padding: 18px 22px;
        border-radius: 10px;
        border: 1px solid #333333;
    }

    .metric-value {
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: -5px;
    }

    .metric-label {
        font-size: 0.8rem;
        font-weight: 300;
        color: #cccccc;
    }

</style>
""", unsafe_allow_html=True)

# Ajuste global de layout (padding e títulos)
st.markdown(
    """
    <style>
        /* reduz o espaço em cima e embaixo do app */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        /* evita título gigante estourando layout */
        h1 {
            font-size: 1.8rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# LOGO
try:
    st.sidebar.write("")
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
# CARREGAR BASE (NOVO – via uploader ou arquivos internos)
# ============================================================

st.sidebar.title("Carregamento da Base")

modo_base = st.sidebar.radio(
    "Como deseja carregar a base?",
    ["Arquivo padrão", "Upload manual (.xlsx)"],
    index=0
)

# Caminho padrão na estrutura atual do projeto:
arquivo_padrao = "Dashboard - Comite Semanal - Brasforma IA (1).xlsx"

data_path = None

if modo_base == "Arquivo padrão":
    data_path = arquivo_padrao

elif modo_base == "Upload manual (.xlsx)":
    uploaded = st.sidebar.file_uploader("Envie sua base (.xlsx)", type=["xlsx"])
    if uploaded is not None:
        data_path = uploaded
    else:
        st.warning("Envie um arquivo para continuar.")
        st.stop()

st.sidebar.caption(f"📄 Arquivo selecionado: **{data_path}**")

# Carregar base usando sua função atual
df = load_brasforma(data_path)

# ============================================================
# SIDEBAR – FILTROS (VERSÃO CORRIGIDA E 100% VÁLIDA)
# ============================================================

st.sidebar.header("Filtros")

# ---- Período ----
min_d = df["Data / Mês"].min()
max_d = df["Data / Mês"].max()

periodo = st.sidebar.date_input(
    "Período",
    value=(min_d, max_d),
    min_value=min_d,
    max_value=max_d,
)

df_f = df[
    (df["Data / Mês"] >= pd.to_datetime(periodo[0])) &
    (df["Data / Mês"] <= pd.to_datetime(periodo[1]))
].copy()

# ---- Transação (COLUNA C DA BASE) ----
# Garante nome correto mesmo que o arquivo venha diferente
col_trans = None
for c in df.columns:
    if c.strip().lower() in ["transacao", "transação", "transaction", "transacao ", "transação "]:
        col_trans = c
        break

# Se não encontrou, assume coluna 3 da base original
if col_trans is None:
    col_trans = df.columns[2]
    df.rename(columns={col_trans: "Transação"}, inplace=True)
    col_trans = "Transação"

transacoes = sorted(df[col_trans].dropna().unique())
trans_sel = st.sidebar.multiselect("Transação", transacoes)

if trans_sel:
    df_f = df_f[df_f[col_trans].isin(trans_sel)]

# ---- Regional ----
if "Regional" in df.columns:
    regionais = sorted(df["Regional"].dropna().unique())
    reg_sel = st.sidebar.multiselect("Regional", regionais)
    if reg_sel:
        df_f = df_f[df_f["Regional"].isin(reg_sel)]

# ---- Representante ----
if "Representante" in df.columns:
    reps = sorted(df["Representante"].dropna().unique())
    rep_sel = st.sidebar.multiselect("Representante", reps)
    if rep_sel:
        df_f = df_f[df_f["Representante"].isin(rep_sel)]

# ---- UF ----
if "UF" in df.columns:
    ufs = sorted(df["UF"].dropna().unique())
    uf_sel = st.sidebar.multiselect("UF", ufs)
    if uf_sel:
        df_f = df_f[df_f["UF"].isin(uf_sel)]

# ---- Status ----
if "Status de Produção / Faturamento" in df.columns:
    status = sorted(df["Status de Produção / Faturamento"].dropna().unique())
    status_sel = st.sidebar.multiselect("Status Prod./Fat.", status)
    if status_sel:
        df_f = df_f[df_f["Status de Produção / Faturamento"].isin(status_sel)]

# ---- Cliente ----
if "Nome Cliente" in df.columns:
    cliente_txt = st.sidebar.text_input("Cliente (contém):")
    if cliente_txt.strip():
        df_f = df_f[
            df_f["Nome Cliente"].astype(str).str.contains(cliente_txt, case=False, na=False)
        ]

# ---- Item / SKU ----
if "ITEM" in df.columns:
    item_txt = st.sidebar.text_input("SKU/Item (contém):")
    if item_txt.strip():
        df_f = df_f[
            df_f["ITEM"].astype(str).str.contains(item_txt, case=False, na=False)
        ]

# ============================================================
# PRÉ-CÁLCULO GLOBAL (seguro) – usado pela Visão Executiva
# ============================================================

# Histórico antes do período filtrado
df_historico_global = df[df["Data / Mês"] < df_f["Data / Mês"].min()]

# Clientes históricos por representante
hist_global = (
    df_historico_global.groupby("Representante")["Nome Cliente"]
    .nunique()
    .rename("ClientesHistoricos")
)

# Clientes atendidos no período atual
periodo_global = (
    df_f.groupby("Representante")["Nome Cliente"]
    .nunique()
    .rename("ClientesAtuais")
)

# Junta tudo corretamente, alinhando índices
rep_global = pd.concat([hist_global, periodo_global], axis=1)

# Preenche faltas com zero
rep_global = rep_global.fillna(0)

# Converte tudo para inteiro
rep_global = rep_global.astype(int)

# Calcula novos e não atendidos
rep_global["QtdClientesNovos"] = (
    rep_global["ClientesAtuais"] - rep_global["ClientesHistoricos"]
).clip(lower=0)

rep_global["QtdClientesNaoAtendidos"] = (
    rep_global["ClientesHistoricos"] - rep_global["ClientesAtuais"]
).clip(lower=0)

# Somatórios globais usados pela Visão Executiva
total_novos_global = int(rep_global["QtdClientesNovos"].sum())
total_nao_global = int(rep_global["QtdClientesNaoAtendidos"].sum())


# ============================================================
# VISÃO EXECUTIVA – COMPLETA, COM RESUMO E IA
# ============================================================

st.markdown("## 📊 Visão Executiva – Panorama Geral")

# --------------------------
# KPIs
# --------------------------
fat_liq = df_f["Faturamento Líquido"].sum()
fat_bruto = df_f["Valor Pedido R$"].sum()
impostos = df_f["Imposto Total"].sum()
pedidos = df_f["Pedido"].nunique()
clientes = df_f["Nome Cliente"].nunique()
custo_total = df_f["Custo Total"].sum()

margem_bruta = ((fat_bruto - custo_total) / fat_bruto * 100) if fat_bruto > 0 else 0
ticket_medio = fat_liq / pedidos if pedidos > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col5, col6, col7, col8 = st.columns(4)

with col1:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Faturamento Líquido</div><div class='metric-value'>{fmt_money(fat_liq)}</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Faturamento Bruto</div><div class='metric-value'>{fmt_money(fat_bruto)}</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Impostos</div><div class='metric-value'>{fmt_money(impostos)}</div></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Pedidos</div><div class='metric-value'>{fmt_int(pedidos)}</div></div>", unsafe_allow_html=True)

with col5:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Clientes Atendidos</div><div class='metric-value'>{fmt_int(clientes)}</div></div>", unsafe_allow_html=True)
with col6:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Custo Total</div><div class='metric-value'>{fmt_money(custo_total)}</div></div>", unsafe_allow_html=True)
with col7:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Margem Bruta (%)</div><div class='metric-value'>{fmt_pct(margem_bruta)}</div></div>", unsafe_allow_html=True)
with col8:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Ticket Médio</div><div class='metric-value'>{fmt_money(ticket_medio)}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# RESUMO EXECUTIVO
# ============================================================

st.markdown("### 📰 Resumo Executivo do Período")

fat_liq_prev = df[df["Data / Mês"] < df_f["Data / Mês"].min()]["Faturamento Líquido"].sum()
pedidos_prev = df[df["Data / Mês"] < df_f["Data / Mês"].min()]["Pedido"].nunique()
clientes_prev = df[df["Data / Mês"] < df_f["Data / Mês"].min()]["Nome Cliente"].nunique()

var_fat = ((fat_liq - fat_liq_prev) / fat_liq_prev * 100) if fat_liq_prev > 0 else 0
var_ped = ((pedidos - pedidos_prev) / pedidos_prev * 100) if pedidos_prev > 0 else 0
var_cli = ((clientes - clientes_prev) / clientes_prev * 100) if clientes_prev > 0 else 0

resumo = f"""
No período analisado, o faturamento líquido foi de **{fmt_money(fat_liq)}**, 
uma variação de **{fmt_pct(var_fat)}** frente ao período anterior.

Foram registrados **{fmt_int(pedidos)} pedidos**, com variação de **{fmt_pct(var_ped)}**, 
e **{fmt_int(clientes)} clientes ativos**, mudança de **{fmt_pct(var_cli)}**.

A margem bruta encerrou em **{fmt_pct(margem_bruta)}**, refletindo o impacto do mix, precificação e carga tributária.
"""

st.info(resumo)

# ============================================================
# INSIGHTS DA IA
# ============================================================

st.markdown("### 🤖 Insights Automáticos da IA Comercial")

insights = []

# Margem
if margem_bruta < 30:
    insights.append(f"Margem bruta baixa ({fmt_pct(margem_bruta)}). Avaliar descontos e composição do mix.")
elif margem_bruta > 45:
    insights.append(f"Margem bruta elevada ({fmt_pct(margem_bruta)}). Mix e preço estão favoráveis.")

# Impostos
perc_imp = (impostos / fat_bruto * 100) if fat_bruto > 0 else 0
if perc_imp > 22:
    insights.append(f"Carga tributária alta ({fmt_pct(perc_imp)}). Impacto significativo no preço final.")
else:
    insights.append(f"Carga tributária dentro do aceitável ({fmt_pct(perc_imp)}).")

# Clientes
if var_cli < 0:
    insights.append("Base de clientes caiu. Ações de reativação devem ser priorizadas.")
elif var_cli > 5:
    insights.append("Base de clientes em expansão. Oportunidade de aumentar recorrência.")

# Concentração
top5 = df_f.groupby("Nome Cliente")["Faturamento Líquido"].sum().nlargest(5)
perc_top5 = top5.sum() / fat_liq * 100 if fat_liq > 0 else 0

if perc_top5 > 45:
    insights.append(f"Concentração elevada: top 5 clientes = {fmt_pct(perc_top5)} do faturamento.")
else:
    insights.append(f"Concentração saudável ({fmt_pct(perc_top5)}).")

# Churn global
if total_nao_global > 40:
    insights.append(f"{fmt_int(total_nao_global)} clientes não atendidos. Risco de churn.")
else:
    insights.append("Clientes não atendidos em nível controlado.")

for item in insights:
    st.warning("• " + item)

st.markdown("---")



st.markdown("### 📈 Evolução Mensal")


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

aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "Clientes",
    "Representantes",
    "UF / Geografia",
    "Produtos / Rentabilidade",
    "Atrasos e Lead Time",
    "RFM"
])


# ============================================================
# CLIENTES – NOVA VERSÃO CORPORATIVA COMPLETA
# ============================================================
with aba1:
    st.subheader("📌 Inteligência de Clientes – Carteira, Tendências e Risco")

    # ============================
    # KPI PRINCIPAIS
    # ============================
    clientes_ativos = df_f["Nome Cliente"].nunique()
    clientes_periodo = set(df_f["Nome Cliente"].unique())

    # Datas para calcular novos e perdidos
    data_ini = df_f["Data / Mês"].min()
    janela_previa_ini = data_ini - pd.DateOffset(months=12)

    df_hist_12m = df[
        (df["Data / Mês"] >= janela_previa_ini) &
        (df["Data / Mês"] < data_ini)
    ]

    clientes_prev = set(df_hist_12m["Nome Cliente"].unique())

    clientes_novos = sorted(clientes_periodo - clientes_prev)
    clientes_perdidos = sorted(clientes_prev - clientes_periodo)

    ticket_medio_cliente = df_f.groupby("Nome Cliente")["Faturamento Líquido"].sum().mean()

    colA, colB, colC, colD = st.columns(4)
    colA.metric("Clientes Ativos", fmt_int(clientes_ativos))
    colB.metric("Clientes Novos", fmt_int(len(clientes_novos)))
    colC.metric("Clientes Perdidos", fmt_int(len(clientes_perdidos)))
    colD.metric("Ticket Médio por Cliente", fmt_money(ticket_medio_cliente))

    st.markdown("---")

    # ============================================================
    # RANKING COMPLETO DE CLIENTES
    # ============================================================
    st.markdown("### 📊 Ranking Completo de Clientes (Faturamento, Ticket, Margem)")

    cli = df_f.groupby("Nome Cliente", as_index=False).agg(
        FatLiq=("Faturamento Líquido","sum"),
        FatBruto=("Valor Pedido R$","sum"),
        Impostos=("Imposto Total","sum"),
        Lucro=("Lucro Bruto","sum"),
        Pedidos=("Pedido","nunique"),
        Qtd=("Quant. Pedidos","sum")
    )

    cli["Ticket Médio"] = cli["FatLiq"] / cli["Pedidos"]
    cli["Margem (%)"] = np.where(cli["FatBruto"] > 0, 100 * cli["Lucro"] / cli["FatBruto"], np.nan)

    cli_fmt = format_dataframe(
        cli.sort_values("FatLiq", ascending=False),
        money_cols=["FatLiq","FatBruto","Lucro","Impostos","Ticket Médio"],
        pct_cols=["Margem (%)"],
        int_cols=["Pedidos","Qtd"]
    )

    st.dataframe(cli_fmt, use_container_width=True)

    st.markdown("---")

    # ============================================================
    # CURVA ABC DOS CLIENTES – com seletor Top N
    # ============================================================
    st.subheader("📈 Curva ABC de Clientes – Concentração de Receita")

    top_n = st.slider(
        "Quantidade de clientes no gráfico (Top N):",
        min_value=5,
        max_value=len(cli),
        value=30,
        step=5
    )

    abc = cli.sort_values("FatLiq", ascending=False).copy()
    abc["% do Total"] = abc["FatLiq"] / abc["FatLiq"].sum() * 100
    abc["% Acum"] = abc["% do Total"].cumsum()
    abc_plot = abc.head(top_n)

    fig_abc = px.line(
        abc_plot,
        x="Nome Cliente",
        y="% Acum",
        title=f"Curva ABC – % Acumulado (Top {top_n} Clientes)",
        markers=True
    )
    fig_abc.update_layout(xaxis_title=None, yaxis_title="% Acumulado")

    st.plotly_chart(fig_abc, use_container_width=True)

    st.markdown("---")

    # ============================================================
    # SELECIONAR CLIENTE PARA DETALHAMENTO
    # ============================================================
    st.subheader("🔍 Análise Individual do Cliente")

    cliente_sel = st.selectbox(
        "Selecione um cliente para análise:",
        sorted(cli["Nome Cliente"])
    )

    df_c = df_f[df_f["Nome Cliente"] == cliente_sel]

    # KPIs individuais
    col1, col2, col3 = st.columns(3)
    col1.metric("Faturamento Líquido", fmt_money(df_c["Faturamento Líquido"].sum()))
    col2.metric("Ticket Médio", fmt_money(df_c["Faturamento Líquido"].sum() / df_c["Pedido"].nunique()))
    col3.metric("Margem (%)", fmt_pct(
        100 * df_c["Lucro Bruto"].sum() / df_c["Valor Pedido R$"].sum()
        if df_c["Valor Pedido R$"].sum() > 0 else 0
    ))

    # ============================================================
    # ALERTAS AUTOMÁTICOS DO CLIENTE
    # ============================================================
    st.markdown("### 🚨 Alertas Automáticos do Cliente")

    alertas = []

    # Faturamento atual vs histórico
    fat_atual = df_c["Faturamento Líquido"].sum()
    fat_prev = df[
        (df["Nome Cliente"] == cliente_sel) &
        (df["Data / Mês"] < data_ini)
    ]["Faturamento Líquido"].sum()

    if fat_prev > 0:
        var_cli = (fat_atual - fat_prev) / fat_prev * 100
        if var_cli < -30:
            alertas.append(f"📉 Queda acentuada de faturamento (**{fmt_pct(var_cli)}**) frente ao período anterior.")
        elif var_cli > 40:
            alertas.append(f"📈 Crescimento expressivo de faturamento (**{fmt_pct(var_cli)}**). Cliente em expansão.")

    # Margem crítica
    margem_cli = df_c["Lucro Bruto"].sum() / df_c["Valor Pedido R$"].sum() * 100 if df_c["Valor Pedido R$"].sum() > 0 else 0
    if margem_cli < 10:
        alertas.append("🔥 Margem muito baixa. Avaliar desconto, mix e carga tributária.")

    # Cliente com risco de churn
    freq = df_c["Pedido"].nunique()
    if freq == 1 and fat_atual < ticket_medio_cliente * 0.5:
        alertas.append("⚠ Cliente com baixa frequência. Risco de churn elevado.")

    # Concentração
    perc_cli = fat_atual / fat_liq * 100 if fat_liq > 0 else 0
    if perc_cli > 15:
        alertas.append(f"🔴 Cliente representa **{fmt_pct(perc_cli)}** do faturamento total. Atenção à dependência.")

    if len(alertas) == 0:
        st.success("Nenhum alerta identificado para este cliente.")
    else:
        for a in alertas:
            st.warning(a)

    st.markdown("---")

    # ============================================================
    # CARDS EXECUTIVOS – Perfil 360°
    # ============================================================
    st.subheader("🧩 Cards Executivos do Cliente")

    colc1, colc2, colc3 = st.columns(3)

    with colc1:
        st.info(f"**Representantes que atendem:**\n{', '.join(df_c['Representante'].dropna().unique())}")

    with colc2:
        st.info(f"**UFs atendidas:**\n{', '.join(df_c['UF'].dropna().unique())}")

    with colc3:
        st.info(f"**Itens Diferentes Comprados:**\n{df_c['ITEM'].nunique()} SKUs")

    st.markdown("---")

    # ============================================================
    # TENDÊNCIA MENSAL DO CLIENTE
    # ============================================================
    df_cli_mes = df_c.groupby("Ano-Mes", as_index=False)["Faturamento Líquido"].sum()
    fig_trend = px.bar(
        df_cli_mes,
        x="Ano-Mes",
        y="Faturamento Líquido",
        title=f"Evolução Mensal – {cliente_sel}"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ============================================================
    # MIX DE PRODUTOS DO CLIENTe
    # ============================================================
    st.markdown("### 🧺 Mix de Produtos Comprados")

    mix_cli = df_c.groupby("ITEM", as_index=False)["Faturamento Líquido"].sum().sort_values("Faturamento Líquido", ascending=False)

    st.dataframe(
        apply_global_formatting(mix_cli),
        use_container_width=True
    )



# ============================================================
# REPRESENTANTES
# ============================================================
with aba2:
    st.subheader("📌 Performance Geral por Representante")

    # ----------------------------------------
    # BASE ATUAL FILTRADA
    # ----------------------------------------
    df_rep_periodo = df_f.copy()

    # ----------------------------------------
    # IDENTIFICAR HISTÓRICO (ANTES DO PERÍODO FILTRADO)
    # ----------------------------------------
    df_historico = df[df["Data / Mês"] < df_f["Data / Mês"].min()]

    historico_por_rep = (
        df_historico.groupby("Representante")["Nome Cliente"]
        .unique()
        .rename("ClientesHistoricos")
    )

    periodo_por_rep = (
        df_rep_periodo.groupby("Representante")["Nome Cliente"]
        .unique()
        .rename("ClientesAtuais")
    )

    # ----------------------------------------
    # COMBINAR HISTÓRICO x PERÍODO ATUAL
    # ----------------------------------------
    clientes_merge = pd.concat(
        [historico_por_rep, periodo_por_rep],
        axis=1
    )

    # ----------------------------------------
    # PROTEÇÃO CONTRA NaN E TIPOS INVÁLIDOS
    # ----------------------------------------
    def safe_list(v):
        if isinstance(v, (list, tuple, np.ndarray, set)):
            return list(v)
        if pd.isna(v):
            return []
        return [v]

    clientes_merge["ClientesHistoricos"] = clientes_merge["ClientesHistoricos"].apply(safe_list)
    clientes_merge["ClientesAtuais"] = clientes_merge["ClientesAtuais"].apply(safe_list)

    # ----------------------------------------
    # CÁLCULO DE NOVOS E NÃO ATENDIDOS
    # ----------------------------------------
    clientes_merge["ClientesNovos"] = clientes_merge.apply(
        lambda x: list(set(x.ClientesAtuais) - set(x.ClientesHistoricos)),
        axis=1
    )

    clientes_merge["ClientesNaoAtendidos"] = clientes_merge.apply(
        lambda x: list(set(x.ClientesHistoricos) - set(x.ClientesAtuais)),
        axis=1
    )

    clientes_merge["QtdClientesNovos"] = clientes_merge["ClientesNovos"].apply(len)
    clientes_merge["QtdClientesNaoAtendidos"] = clientes_merge["ClientesNaoAtendidos"].apply(len)

    # ----------------------------------------
    # PERFORMANCE NUMÉRICA PRINCIPAL
    # ----------------------------------------
    rep = df_rep_periodo.groupby("Representante", as_index=False).agg(
        FatLiq=("Faturamento Líquido", "sum"),
        FatBruto=("Valor Pedido R$", "sum"),
        Impostos=("Imposto Total", "sum"),
        CustoTotal=("Custo Total", "sum"),
        Pedidos=("Pedido", "nunique"),
        ClientesAtivos=("Nome Cliente", "nunique"),
        QtdItens=("Quant. Pedidos", "sum")
    )

    rep["Ticket Médio"] = rep["FatLiq"] / rep["Pedidos"]
    rep["Margem Bruta (%)"] = np.where(
        rep["FatBruto"] > 0,
        100 * (rep["FatBruto"] - rep["CustoTotal"]) / rep["FatBruto"],
        np.nan
    )
    rep["Margem Líquida (%)"] = np.where(
        rep["FatLiq"] > 0,
        100 * (rep["FatLiq"] - rep["CustoTotal"]) / rep["FatLiq"],
        np.nan
    )
    rep["% Impostos"] = rep["Impostos"] / rep["FatBruto"] * 100

    # ----------------------------------------
    # MERGE COM CLIENTES NOVOS E NÃO ATENDIDOS
    # ----------------------------------------
    rep = rep.merge(
        clientes_merge[
            ["ClientesNovos", "ClientesNaoAtendidos", "QtdClientesNovos", "QtdClientesNaoAtendidos"]
        ],
        left_on="Representante",
        right_index=True,
        how="left"
    )

    # Ajuste final de listas e inteiros
    rep["ClientesNovos"] = rep["ClientesNovos"].apply(lambda x: x if isinstance(x, list) else [])
    rep["ClientesNaoAtendidos"] = rep["ClientesNaoAtendidos"].apply(lambda x: x if isinstance(x, list) else [])
    rep["QtdClientesNovos"] = rep["QtdClientesNovos"].fillna(0).astype(int)
    rep["QtdClientesNaoAtendidos"] = rep["QtdClientesNaoAtendidos"].fillna(0).astype(int)

    # ----------------------------------------
    # FORMATAÇÃO CORPORATIVA
    # ----------------------------------------
    rep_fmt = format_dataframe(
        rep.sort_values("FatLiq", ascending=False),
        money_cols=["FatLiq", "FatBruto", "Impostos", "CustoTotal", "Ticket Médio"],
        pct_cols=["Margem Bruta (%)", "Margem Líquida (%)", "% Impostos"],
        int_cols=["Pedidos", "ClientesAtivos", "QtdItens", "QtdClientesNovos", "QtdClientesNaoAtendidos"]
    )

    st.dataframe(rep_fmt, use_container_width=True)

    # ============================================================
    # DETALHAMENTO POR REPRESENTANTE – DENTRO DA ABA
    # ============================================================
    st.markdown("## 👥 Detalhamento por Representante")

    rep_select = st.selectbox(
        "Selecione o Representante",
        rep["Representante"].unique()
    )

    det = rep[rep["Representante"] == rep_select].iloc[0]

    col1, col2 = st.columns(2)

    # ----------------- Clientes novos -----------------
    with col1:
        st.write("### 🟢 Clientes Novos Atendidos no Período")
        clientes_novos_list = det["ClientesNovos"]

        if len(clientes_novos_list) == 0:
            st.info("Nenhum cliente novo atendido no período.")
        else:
            tabela_novos = pd.DataFrame({"Clientes Novos": clientes_novos_list})
            st.dataframe(tabela_novos, use_container_width=True)

    # ------------- Clientes não atendidos --------------
    with col2:
        st.write("### 🔴 Clientes Não Atendidos")
        clientes_nao_list = det["ClientesNaoAtendidos"]

        if len(clientes_nao_list) == 0:
            st.success("Nenhum cliente perdido ou não atendido no período.")
        else:
            tabela_nao = pd.DataFrame({"Clientes Não Atendidos": clientes_nao_list})
            st.dataframe(tabela_nao, use_container_width=True)

# ============================================================
# UF / GEOGRAFIA – VERSÃO PREMIUM FINAL COM INDENTAÇÃO CORRETA
# ============================================================
with aba3:
    st.subheader("🌎 Inteligência Geográfica – Visão Premium por UF")

    # ============================================================
    # KPI TERRITORIAIS ESTRATÉGICOS
    # ============================================================
    geo = df_f.groupby("UF", as_index=False).agg(
        FatLiq=("Faturamento Líquido","sum"),
        FatBruto=("Valor Pedido R$","sum"),
        Impostos=("Imposto Total","sum"),
        Pedidos=("Pedido","nunique"),
        Clientes=("Nome Cliente","nunique"),
        Custo=("Custo Total","sum"),
        Itens=("Quant. Pedidos","sum")
    )

    geo["Margem (%)"] = np.where(
        geo["FatBruto"] > 0,
        100 * (geo["FatBruto"] - geo["Custo"]) / geo["FatBruto"],
        np.nan
    )
    geo["Ticket Médio"] = np.where(geo["Pedidos"] > 0, geo["FatLiq"] / geo["Pedidos"], np.nan)
    geo["% Part"] = geo["FatLiq"] / geo["FatLiq"].sum() * 100 if geo["FatLiq"].sum() > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturamento Líquido Total", fmt_money(geo["FatLiq"].sum()))
    col2.metric("UFs Ativas", fmt_int(geo["UF"].nunique()))
    col3.metric("Ticket Médio Geral", fmt_money(geo["Ticket Médio"].mean()))
    col4.metric("Margem Média (%)", fmt_pct(geo["Margem (%)"].mean()))

    uf_top = geo.sort_values("FatLiq", ascending=False).iloc[0]
    col5, col6 = st.columns(2)
    col5.success(f"🏆 UF Líder em Faturamento: **{uf_top['UF']}**")
    col6.info(f"Participação: **{fmt_pct(uf_top['% Part'])}**")

    st.markdown("---")

    # ============================================================
    # MAPA INTERATIVO DO BRASIL – SEM GEOJSON EXTERNO
    # ============================================================
    st.subheader("🗺️ Mapa de Faturamento por UF")

    uf_iso = {
        "AC":"BR-AC","AL":"BR-AL","AP":"BR-AP","AM":"BR-AM","BA":"BR-BA","CE":"BR-CE",
        "DF":"BR-DF","ES":"BR-ES","GO":"BR-GO","MA":"BR-MA","MT":"BR-MT","MS":"BR-MS",
        "MG":"BR-MG","PA":"BR-PA","PB":"BR-PB","PR":"BR-PR","PE":"BR-PE","PI":"BR-PI",
        "RJ":"BR-RJ","RN":"BR-RN","RO":"BR-RO","RR":"BR-RR","RS":"BR-RS","SC":"BR-SC",
        "SE":"BR-SE","SP":"BR-SP","TO":"BR-TO"
    }

    geo["UF_Code"] = geo["UF"].map(uf_iso)

    fig_map = px.choropleth(
        geo,
        locations="UF_Code",
        color="FatLiq",
        color_continuous_scale="Viridis",
        locationmode="ISO-3166-2",
        hover_name="UF",
        hover_data={
            "FatLiq": ":,.2f",
            "Margem (%)": ":.1f",
            "Clientes": True,
            "Pedidos": True
        },
        title="Faturamento por UF – Mapa Interativo"
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("---")

    # ============================================================
    # CURVA ABC DE UFs
    # ============================================================
    st.subheader("📈 Curva ABC de UFs – Concentração Geográfica")

    top_ufs = st.slider(
        "Quantidade de UFs no gráfico (Top N):",
        min_value=3,
        max_value=len(geo),
        value=10,
        step=1
    )

    abc_uf = geo.sort_values("FatLiq", ascending=False).copy()
    abc_uf["% Total"] = abc_uf["FatLiq"] / abc_uf["FatLiq"].sum() * 100
    abc_uf["% Acum"] = abc_uf["% Total"].cumsum()

    fig_abc_uf = px.line(
        abc_uf.head(top_ufs),
        x="UF",
        y="% Acum",
        markers=True,
        title=f"Curva ABC – {top_ufs} UFs com Maior Faturamento"
    )

    fig_abc_uf.update_layout(yaxis_title="% Acumulado", xaxis_title=None)
    st.plotly_chart(fig_abc_uf, use_container_width=True)

    st.markdown("---")

    # ============================================================
    # DETALHAMENTO POR UF
    # ============================================================
    st.subheader("🔍 Análise Individual por UF")

    uf_sel = st.selectbox("Selecione uma UF:", sorted(geo["UF"].unique()))
    df_u = df_f[df_f["UF"] == uf_sel]

    colUF1, colUF2, colUF3, colUF4 = st.columns(4)
    colUF1.metric("Faturamento Líquido", fmt_money(df_u["Faturamento Líquido"].sum()))
    colUF2.metric("Pedidos", fmt_int(df_u["Pedido"].nunique()))
    colUF3.metric("Clientes Atendidos", fmt_int(df_u["Nome Cliente"].nunique()))

    margem_uf = (
        df_u["Lucro Bruto"].sum() / df_u["Valor Pedido R$"].sum() * 100
        if df_u["Valor Pedido R$"].sum() > 0 else 0
    )
    colUF4.metric("Margem (%)", fmt_pct(margem_uf))

    # ============================================================
    # ALERTAS DA UF
    # ============================================================
    st.markdown("### 🚨 Alertas Automáticos da UF")

    alertas_uf = []

    fat_u_atual = df_u["Faturamento Líquido"].sum()
    fat_u_prev = df[
        (df["UF"] == uf_sel) &
        (df["Data / Mês"] < data_ini)
    ]["Faturamento Líquido"].sum()

    if fat_u_prev > 0:
        var_uf = (fat_u_atual - fat_u_prev) / fat_u_prev * 100
        if var_uf < -25:
            alertas_uf.append(f"📉 Queda relevante de faturamento (**{fmt_pct(var_uf)}**) frente ao período anterior.")
        elif var_uf > 35:
            alertas_uf.append(f"📈 Forte expansão (**{fmt_pct(var_uf)}**) frente ao período anterior.")

    if margem_uf < 12:
        alertas_uf.append("🔥 Margem baixa na região. Avaliar mix e desconto aplicado.")

    clientes_periodo_u = set(df_u["Nome Cliente"].unique())
    clientes_hist_u = set(
        df[(df["UF"] == uf_sel) & (df["Data / Mês"] < data_ini)]["Nome Cliente"].unique()
    )
    perdidos_u = clientes_hist_u - clientes_periodo_u

    if len(perdidos_u) > 10:
        alertas_uf.append("⚠ Churn elevado de clientes nesta UF.")

    perc_uf = fat_u_atual / geo["FatLiq"].sum() * 100 if geo["FatLiq"].sum() > 0 else 0
    if perc_uf > 20:
        alertas_uf.append(f"🔴 UF representa **{fmt_pct(perc_uf)}** do faturamento total. Alto risco de dependência.")

    if len(alertas_uf) == 0:
        st.success("Nenhum alerta crítico identificado nesta UF.")
    else:
        for a in alertas_uf:
            st.warning(a)

    st.markdown("---")

    # ============================================================
    # TOP CLIENTES DA UF
    # ============================================================
    st.subheader("🏅 Top Clientes da UF")

    top_cli_uf = (
        df_u.groupby("Nome Cliente", as_index=False)
        .agg(FatLiq=("Faturamento Líquido","sum"))
        .sort_values("FatLiq", ascending=False)
        .head(15)
    )

    st.dataframe(apply_global_formatting(top_cli_uf), use_container_width=True)

    # ============================================================
    # MIX DE PRODUTOS DA UF
    # ============================================================
    st.subheader("🧺 Mix de Produtos da UF")

    mix_u = (
        df_u.groupby("ITEM", as_index=False)["Faturamento Líquido"]
        .sum()
        .sort_values("Faturamento Líquido", ascending=False)
        .head(20)
    )

    st.dataframe(apply_global_formatting(mix_u), use_container_width=True)

    # ============================================================
    # TENDÊNCIA DA UF
    # ============================================================
    df_u_mes = df_u.groupby("Ano-Mes", as_index=False)["Faturamento Líquido"].sum()

    fig_u_trend = px.line(
        df_u_mes,
        x="Ano-Mes",
        y="Faturamento Líquido",
        markers=True,
        title=f"Evolução Mensal – {uf_sel}"
    )

    st.plotly_chart(fig_u_trend, use_container_width=True)



# ============================================================
# PRODUTOS / RENTABILIDADE
# ============================================================
with aba4:
    st.subheader("Rentabilidade por ITEM")

    sku = df_f.groupby("ITEM", as_index=False).agg(
        FatLiq=("Faturamento Líquido","sum"),
        Custo=("Custo Total","sum"),
        Lucro=("Lucro Bruto","sum"),
        Qtd=("Quant. Pedidos","sum"),
    )

    sku_fmt = apply_global_formatting(sku.sort_values("FatLiq", ascending=False))

    st.dataframe(sku_fmt, use_container_width=True)


# ============================================================
# ATRASOS / LEAD TIME
# ============================================================
with aba5:
    st.subheader("Análise de Atrasos")

    atrasos = df_f.groupby("AtrasadoFlag", as_index=False).agg(
        Pedidos=("Pedido","nunique")
    )

    atrasos_fmt = apply_global_formatting(atrasos)

    st.dataframe(atrasos_fmt, use_container_width=True)


# ============================================================
# INTELIGÊNCIA COMERCIAL
# ============================================================
st.header("🧠 Inteligência Comercial")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Clientes em Crescimento",
    "Clientes em Queda",
    "Tendência de SKUs",
    "Cesta por Região",
    "Anomalias"
])

with tab1:
    st.subheader("Clientes em Crescimento (Emergentes)")
    st.dataframe(apply_global_formatting(clientes_em_crescimento(df_f)))

with tab2:
    st.subheader("Clientes em Queda (Risco)")
    st.dataframe(apply_global_formatting(clientes_em_queda(df_f)))

with tab3:
    st.subheader("Tendência de SKUs")
    st.dataframe(apply_global_formatting(skus_em_tendencia(df_f)))

with tab4:
    st.subheader("Cesta Comercial por Região (Top 5)")
    st.dataframe(apply_global_formatting(cesta_por_regiao(df_f)))

with tab5:
    st.subheader("Anomalias Comerciais")
    st.dataframe(apply_global_formatting(detectar_anomalias(df_f)))
    
   # ============================================================
# ABA 6 – RFM (Recência, Frequência, Monetário)
# ============================================================
with aba6:
    st.subheader("📊 Análise RMF – Recência, Frequência e Monetário")

    # =============================
    # CÁLCULO DA RECÊNCIA
    # =============================
    max_date = df_f["Data do Pedido"].max()

    rfm = df_f.groupby("Nome Cliente").agg(
        Recencia=("Data do Pedido", lambda x: (max_date - x.max()).days),
        Frequencia=("Pedido", "nunique"),
        Monetario=("Faturamento Líquido", "sum"),
        Representantes=("Representante", lambda x: list(set(x))),
        UFs=("UF", lambda x: list(set(x)))
    ).reset_index()

    # =============================
    # SEGMENTAÇÃO RFM (Executiva)
    # =============================
    def classificar_rfm(row):
        r, f, m = row["Recencia"], row["Frequencia"], row["Monetario"]

        if r <= 30 and f >= 3 and m >= rfm["Monetario"].median():
            return "🔥 VIP / Premium"
        if r <= 45 and f >= 2:
            return "📈 Crescentes"
        if r > 60 and f == 1:
            return "⚠ Clientes Oportunidade"
        if r > 90:
            return "❌ Inativos / Risco"
        return "🟡 Regulares"

    rfm["Segmento"] = rfm.apply(classificar_rfm, axis=1)

    # ============================================================
    # FILTROS INTERNOS DA ABA RMF
    # ============================================================

    st.write("### 🔎 Filtros RFM Específicos")

    colf1, colf2, colf3 = st.columns(3)

    # Representante
    reps_rfm = colf1.multiselect(
        "Representante",
        sorted(df["Representante"].dropna().unique())
    )

    # Segmento
    segs_rfm = colf2.multiselect(
        "Segmento RFM",
        sorted(rfm["Segmento"].unique())
    )

    # UF
    ufs_rfm = colf3.multiselect(
        "UF",
        sorted(df["UF"].dropna().unique())
    )

    # Filtros numéricos
    colf4, colf5, colf6 = st.columns(3)

    rec_max = colf4.slider(
        "Recência Máxima (dias)",
        int(rfm["Recencia"].min()),
        int(rfm["Recencia"].max()),
        int(rfm["Recencia"].max())
    )

    freq_min = colf5.number_input(
        "Frequência mínima",
        min_value=int(rfm["Frequencia"].min()),
        max_value=int(rfm["Frequencia"].max()),
        value=int(rfm["Frequencia"].min())
    )

    monet_min = colf6.number_input(
        "Monetário mínimo (R$)",
        min_value=0.0,
        value=0.0,
        step=100.0
    )

    # ============================================================
    # APLICAR FILTROS INTERNOS
    # ============================================================

    rfm_f = rfm.copy()

    if len(reps_rfm) > 0:
        rfm_f = rfm_f[rfm_f["Representantes"].apply(lambda x: any(r in x for r in reps_rfm))]

    if len(segs_rfm) > 0:
        rfm_f = rfm_f[rfm_f["Segmento"].isin(segs_rfm)]

    if len(ufs_rfm) > 0:
        rfm_f = rfm_f[rfm_f["UFs"].apply(lambda x: any(u in x for u in ufs_rfm))]

    rfm_f = rfm_f[
        (rfm_f["Recencia"] <= rec_max) &
        (rfm_f["Frequencia"] >= freq_min) &
        (rfm_f["Monetario"] >= monet_min)
    ]

    # ============================================================
    # FORMATAÇÃO CORPORATIVA
    # ============================================================

    rfm_fmt = format_dataframe(
        rfm_f.sort_values("Monetario", ascending=False),
        money_cols=["Monetario"],
        pct_cols=[],
        int_cols=["Recencia", "Frequencia"]
    )

    st.dataframe(rfm_fmt, use_container_width=True)

    # ============================================================
    # GRÁFICO RMF
    # ============================================================
    st.subheader("Distribuição por Segmento RFM – Após Filtros")

    seg = rfm_f["Segmento"].value_counts().reset_index()
    seg.columns = ["Segmento", "Clientes"]

    fig_rfm = px.bar(
        seg,
        x="Segmento",
        y="Clientes",
        color="Segmento",
        title="Segmentação RFM – Clientes por Grupo (Filtrados)"
    )
    st.plotly_chart(fig_rfm, use_container_width=True)




# ============================================================
# RODAPÉ
# ============================================================

st.markdown("---")
st.caption("Powered by Brasforma • Arquitetura Comercial Inteligente • IA aplicada a dados corporativos.")
