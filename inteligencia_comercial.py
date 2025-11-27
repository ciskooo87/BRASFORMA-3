import pandas as pd
import numpy as np

# -------------------------------------------------------------
# AUXILIAR
# -------------------------------------------------------------

def _prep(df):
    """Prepara dados mínimos para inteligência"""
    base = df.copy()
    base = base.dropna(subset=["Nome Cliente", "ITEM", "Ano-Mes"])
    return base


# -------------------------------------------------------------
# (A) CLIENTES EM CRESCIMENTO
# -------------------------------------------------------------
def clientes_em_crescimento(df):
    base = _prep(df)

    grp = base.groupby(["Nome Cliente", "Ano-Mes"], as_index=False).agg(
        FatLiq=("Faturamento Líquido", "sum")
    )

    grp["FatLiqAnterior"] = grp.groupby("Nome Cliente")["FatLiq"].shift(1)
    grp["Variacao_%"] = (grp["FatLiq"] - grp["FatLiqAnterior"]) / grp["FatLiqAnterior"] * 100

    # Critérios de crescimento consistente
    crec = grp.groupby("Nome Cliente").agg(
        CrescMediana=("Variacao_%", "median"),
        FaturamentoTotal=("FatLiq", "sum"),
        MesesPositivos=("Variacao_%", lambda x: (x > 0).sum()),
        TotalMeses=("Variacao_%", "count")
    ).reset_index()

    # Lógica executiva
    crec = crec[
        (crec["MesesPositivos"] >= 2) &
        (crec["CrescMediana"] > 10)
    ]

    crec = crec.sort_values("CrescMediana", ascending=False)

    return crec


# -------------------------------------------------------------
# (B) CLIENTES EM QUEDA (RISCO)
# -------------------------------------------------------------
def clientes_em_queda(df):
    base = _prep(df)

    grp = base.groupby(["Nome Cliente", "Ano-Mes"], as_index=False).agg(
        FatLiq=("Faturamento Líquido", "sum")
    )

    grp["FatLiqAnterior"] = grp.groupby("Nome Cliente")["FatLiq"].shift(1)
    grp["Variacao_%"] = (grp["FatLiq"] - grp["FatLiqAnterior"]) / grp["FatLiqAnterior"] * 100

    risco = grp.groupby("Nome Cliente").agg(
        QuedasSeguidas=("Variacao_%", lambda x: (x < -10).sum()),
        QuedaMediana=("Variacao_%", "median"),
        FaturamentoTotal=("FatLiq", "sum"),
        UltimoFaturamento=("FatLiq", lambda x: x.tail(1).values[0])
    ).reset_index()

    risco = risco[
        (risco["QuedasSeguidas"] >= 2) |
        (risco["UltimoFaturamento"] <= risco["FaturamentoTotal"] * 0.10)
    ]

    risco = risco.sort_values("QuedaMediana")

    return risco


# -------------------------------------------------------------
# (C) SKUs EM TENDÊNCIA (ALTA / BAIXA)
# -------------------------------------------------------------
def skus_em_tendencia(df):
    base = _prep(df)

    grp = base.groupby(["ITEM", "Ano-Mes"], as_index=False).agg(
        FatLiq=("Faturamento Líquido", "sum"),
        Qtd=("Quant. Pedidos", "sum"),
    )

    grp["FatAnterior"] = grp.groupby("ITEM")["FatLiq"].shift(1)
    grp["Variacao_%"] = (grp["FatLiq"] - grp["FatAnterior"]) / grp["FatAnterior"] * 100

    trend = grp.groupby("ITEM").agg(
        Cresc3M=("Variacao_%", lambda x: x.tail(3).mean()),
        FatTotal=("FatLiq", "sum"),
        QtdTotal=("Qtd", "sum")
    ).reset_index()

    trend["Tendencia"] = np.where(trend["Cresc3M"] > 5, "Alta",
                           np.where(trend["Cresc3M"] < -5, "Baixa", "Estável"))

    trend = trend.sort_values("Cresc3M", ascending=False)

    return trend


# -------------------------------------------------------------
# (D) CESTA POR REGIÃO (TOP SKUs por UF)
# -------------------------------------------------------------
def cesta_por_regiao(df):
    base = _prep(df)

    grp = base.groupby(["UF", "ITEM"], as_index=False).agg(
        FatLiq=("Faturamento Líquido", "sum")
    )

    total_uf = grp.groupby("UF")["FatLiq"].transform("sum")
    grp["Participacao_%"] = grp["FatLiq"] / total_uf * 100

    top = grp.sort_values(["UF", "Participacao_%"], ascending=[True, False])

    # Top 5 por UF
    top5 = top.groupby("UF").head(5)

    return top5


# -------------------------------------------------------------
# (E) DETECÇÃO DE ANOMALIAS
# -------------------------------------------------------------
def detectar_anomalias(df):
    base = df.copy()

    anomalies = []

    # 1) Pedido fora da curva
    q3 = base["Valor Pedido R$"].quantile(0.75)
    lim = q3 * 2.5  # Muito acima da mediana
    out = base[base["Valor Pedido R$"] > lim]

    for _, row in out.iterrows():
        anomalies.append({
            "Tipo": "Pedido gigante fora do padrão",
            "Pedido": row["Pedido"],
            "Cliente": row["Nome Cliente"],
            "Valor": row["Valor Pedido R$"],
        })

    # 2) Margem muito alta
    marg_out = base[base["Margem %"] > base["Margem %"].quantile(0.99)]
    for _, row in marg_out.iterrows():
        anomalies.append({
            "Tipo": "Margem extremamente alta",
            "Pedido": row["Pedido"],
            "Cliente": row["Nome Cliente"],
            "Valor": row["Margem %"],
        })

    # 3) SKU com custo inadequado
    custo_out = base[base["Custo Total"] < 0]
    for _, row in custo_out.iterrows():
        anomalies.append({
            "Tipo": "Custo negativo (erro de base)",
            "Pedido": row["Pedido"],
            "Cliente": row["Nome Cliente"],
            "Valor": row["Custo Total"],
        })

    return pd.DataFrame(anomalies)
