"""Registrar, listar, editar e excluir produções (RF02, RF03, RF08, RF19)."""

from flask import (Blueprint, flash, g, jsonify, redirect, render_template,
                   request, url_for)

from ..constantes import PERIODOS, PLURAIS
from ..extensions import db
from ..models import Produto
from ..services.calculos import filtrar, mes_atual, meus_produtos, montar_producao
from ..services.catalogo import catalogo_por_categoria

bp = Blueprint("producao", __name__)


def _minha(produto_id):
    produto = db.get_or_404(Produto, produto_id)
    if produto.user_id != g.user.id:          # RF09: nunca mostrar dado de outra pessoa
        from flask import abort
        abort(404)
    return produto


@bp.route("/producao")
def listar():
    filtro = request.args.get("filtro", "todos")
    produtos = filtrar(meus_produtos(), filtro)
    return render_template(
        "producao.html",
        ativo="producao",
        produtos=produtos,
        filtro=filtro,
        grupos=catalogo_por_categoria(request.args.get("categoria"), g.user.id),
        periodos=PERIODOS,
        plurais=PLURAIS,
        mes_atual=mes_atual(),
    )


@bp.route("/producao/adicionar", methods=["POST"])
def adicionar():
    campos, erro = montar_producao(request.form, g.user.id)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("producao.listar"))

    db.session.add(Produto(user_id=g.user.id, **campos))
    db.session.commit()
    flash("Produção registrada.", "sucesso")
    return redirect(url_for("producao.listar"))


@bp.route("/producao/<int:produto_id>/editar", methods=["GET", "POST"])
def editar(produto_id):
    produto = _minha(produto_id)

    if request.method == "POST":
        dados = request.form.to_dict()
        dados["nome"] = produto.nome            # o produto não muda; só os números
        campos, erro = montar_producao(dados, g.user.id, base=produto)
        if erro:
            flash(erro, "erro")
        else:
            for chave, valor in campos.items():
                setattr(produto, chave, valor)
            db.session.commit()
            flash("Produção atualizada.", "sucesso")
            return redirect(url_for("producao.listar"))

    return render_template("producao_editar.html", ativo="producao", p=produto,
                           periodos=PERIODOS, plurais=PLURAIS)


@bp.route("/producao/<int:produto_id>/remover", methods=["POST"])
def remover(produto_id):
    db.session.delete(_minha(produto_id))
    db.session.commit()
    flash("Produção excluída.", "sucesso")
    return redirect(url_for("producao.listar"))


@bp.route("/producao/nova", methods=["POST"])
def nova():
    Produto.query.filter_by(user_id=g.user.id).delete()
    db.session.commit()
    flash("Nova produção iniciada.", "sucesso")
    return redirect(url_for("producao.listar"))


@bp.route("/producao/sincronizar", methods=["POST"])
def sincronizar():
    """Recebe os registros feitos sem internet (RF19) e valida cada um."""
    itens = (request.get_json(silent=True) or {}).get("itens", [])
    resultados = []
    for dados in itens[:100]:
        campos, erro = montar_producao(dados, g.user.id)
        if erro:
            resultados.append({"ok": False, "erro": erro})
        else:
            db.session.add(Produto(user_id=g.user.id, **campos))
            resultados.append({"ok": True})
    db.session.commit()
    return jsonify(resultados=resultados)
