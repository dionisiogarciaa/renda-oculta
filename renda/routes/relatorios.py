"""Calendário produtivo e relatórios (RF13, RF14, RF23)."""

from urllib.parse import quote

from flask import Blueprint, g, render_template, request, send_file

from ..services.calculos import (calcular_totais, meus_produtos, nome_mes,
                                 resumo_por_mes)
from ..services.pdf import gerar_pdf, reais

bp = Blueprint("relatorios", __name__)


def _periodo():
    """Produções do período escolhido (?mes=AAAA-MM ou acumulado)."""
    todos = meus_produtos()
    resumo = resumo_por_mes(todos)
    mes = request.args.get("mes", "acumulado")
    if mes not in {m["mes"] for m in resumo}:
        mes = "acumulado"
    produtos = todos if mes == "acumulado" else [p for p in todos if p.referencia == mes]
    titulo = "Acumulado" if mes == "acumulado" else nome_mes(mes)
    return mes, titulo, produtos, resumo


@bp.route("/calendario")
def calendario():
    resumo = list(reversed(resumo_por_mes(meus_produtos())))
    return render_template("calendario.html", ativo="mais", resumo=resumo)


@bp.route("/relatorios")
def relatorio():
    mes, titulo, produtos, resumo = _periodo()
    totais = calcular_totais(produtos)

    texto = (
        f"Renda Oculta — {titulo}\n"
        f"Valor econômico (estimado): {reais(totais['renda_oculta'])}\n"
        f"Renda monetária (venda): {reais(totais['total_venda'])}\n"
        f"Autoconsumo, trocas e doações são valores estimados, não dinheiro recebido."
    )
    return render_template(
        "relatorios.html", ativo="mais", mes=mes, titulo=titulo, resumo=resumo,
        meses=[(m["mes"], m["nome"]) for m in reversed(resumo)],
        totais=totais, n=len(produtos),
        grafico=[[m["curto"], round(m["valor"], 2), round(m["venda"], 2)] for m in resumo],
        whatsapp="https://wa.me/?text=" + quote(texto),
    )


@bp.route("/relatorios/pdf")
def pdf():
    mes, titulo, produtos, resumo = _periodo()
    arquivo = gerar_pdf(g.user, titulo, produtos, resumo, calcular_totais(produtos))
    return send_file(arquivo, mimetype="application/pdf", download_name=f"relatorio-{mes}.pdf")
