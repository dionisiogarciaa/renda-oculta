"""Visão agregada e anonimizada para cooperativas/extensionistas (RF24)."""

from collections import defaultdict

from flask import Blueprint, abort, g, render_template

from ..models import Produto, User
from ..services.calculos import calcular_totais

bp = Blueprint("agregado", __name__)

MIN_FAMILIAS = 3   # abaixo disso, mostrar números identificaria alguém


@bp.route("/agregado")
def ver():
    if g.user.papel != "agregador":
        abort(403)

    produtos = Produto.query.filter(Produto.user_id.isnot(None)).all()
    familias = {p.user_id for p in produtos}
    liberado = len(familias) >= MIN_FAMILIAS

    dados = {"familias": len(familias), "liberado": liberado, "minimo": MIN_FAMILIAS}

    if liberado:
        totais = calcular_totais(produtos)
        por_produto = defaultdict(float)
        for p in produtos:
            por_produto[p.nome] += p.valor_total * p.fator_mensal

        # por município: só grupos com o mínimo de famílias
        por_mun = defaultdict(lambda: {"ids": set(), "valor": 0.0})
        municipios = dict(User.query.with_entities(User.id, User.municipio))
        for p in produtos:
            g_ = por_mun[municipios.get(p.user_id) or "Não informado"]
            g_["ids"].add(p.user_id)
            g_["valor"] += p.valor_total * p.fator_mensal

        dados.update(
            totais=totais,
            produtos=sorted(por_produto.items(), key=lambda i: -i[1])[:10],
            municipios=sorted(
                ((n, len(v["ids"]), v["valor"]) for n, v in por_mun.items() if len(v["ids"]) >= MIN_FAMILIAS),
                key=lambda i: -i[2]),
        )
    return render_template("agregado.html", ativo="mais", d=dados)
