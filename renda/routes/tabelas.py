"""Tabela de preços de referência (CEASA)."""

from datetime import datetime

from flask import Blueprint, current_app, redirect, render_template, url_for

from ..extensions import db
from ..models import Tabela_Preco

bp = Blueprint("tabelas", __name__)


def _data_atualizacao():
    """Data do último boletim importado (arquivo precos_ceasa.json)."""
    caminho = current_app.config["JSON_PRECOS"]
    if not caminho.exists():
        return ""
    return datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%d/%m/%Y")


@bp.route("/tabela")
def tabela():

    # Categorias na ordem em que aparecem no boletim
    categorias = []

    for (categoria,) in db.session.query(
        Tabela_Preco.categoria
    ).order_by(Tabela_Preco.id):

        if categoria not in categorias:

            categorias.append(categoria)


    return render_template(
        "tabela.html",
        ativo="mais",
        categorias=categorias,
        fonte=current_app.config["FONTE_PRECOS"],
        atualizado=_data_atualizacao()
    )


@bp.route("/tabela/<path:categoria>")
def tabela_categoria(categoria):

    produtos = Tabela_Preco.query.filter_by(
        categoria=categoria
    ).order_by(
        Tabela_Preco.nome
    ).all()


    if not produtos:

        return redirect(
            url_for("tabela")
        )


    return render_template(
        "tabela_categoria.html",
        ativo="mais",
        produtos=produtos,
        categoria=categoria
    )