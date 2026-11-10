"""Produtos e unidades criados pelo agricultor (RF22)."""

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..constantes import UNIDADES_PROPRIAS
from ..extensions import db
from ..models import ProdutoPersonalizado
from ..services.calculos import ler_numero

bp = Blueprint("meus", __name__)


@bp.route("/meus-produtos")
def listar():
    itens = ProdutoPersonalizado.query.filter_by(user_id=g.user.id).order_by(ProdutoPersonalizado.nome).all()
    return render_template("meus_produtos.html", ativo="mais", itens=itens,
                           unidades=list(UNIDADES_PROPRIAS))


@bp.route("/meus-produtos/criar", methods=["POST"])
def criar():
    nome = (request.form.get("nome") or "").strip()[:100]
    rotulo = request.form.get("rotulo", "")
    try:
        preco = ler_numero(request.form.get("preco"))
    except ValueError:
        preco = 0

    if not nome:
        flash("Informe o nome do produto.", "erro")
    elif rotulo not in UNIDADES_PROPRIAS:
        flash("Escolha a unidade de medida.", "erro")
    elif preco <= 0:
        flash("Informe um preço maior que zero.", "erro")
    elif ProdutoPersonalizado.query.filter_by(user_id=g.user.id, nome=nome).first():
        flash("Você já tem um produto com esse nome.", "erro")
    else:
        db.session.add(ProdutoPersonalizado(
            user_id=g.user.id, nome=nome, rotulo=rotulo,
            medida=UNIDADES_PROPRIAS[rotulo], preco_unit=preco))
        db.session.commit()
        flash("Produto criado. Ele aparece em “Meus produtos” ao registrar a produção.", "sucesso")
    return redirect(url_for("meus.listar"))


@bp.route("/meus-produtos/<int:item_id>/excluir", methods=["POST"])
def excluir(item_id):
    item = db.get_or_404(ProdutoPersonalizado, item_id)
    if item.user_id != g.user.id:
        abort(404)
    db.session.delete(item)          # produções já registradas guardam o próprio preço/unidade
    db.session.commit()
    flash("Produto removido da sua lista.", "sucesso")
    return redirect(url_for("meus.listar"))
