"""Perfil, lembretes, exportação e exclusão da conta (RF15, RF21, LGPD)."""

import json
from datetime import datetime

from flask import (Blueprint, Response, flash, g, redirect, render_template,
                   request, session, url_for)

from ..extensions import db
from ..models import Produto, ProdutoPersonalizado, User

bp = Blueprint("perfil", __name__)


@bp.route("/perfil", methods=["GET", "POST"])
def ver():
    if request.method == "POST":
        f = request.form
        nome = (f.get("nome") or "").strip()
        if not nome:
            flash("Informe o seu nome.", "erro")
        else:
            g.user.nome = nome[:100]
            g.user.comunidade = (f.get("comunidade") or "").strip()[:100] or None
            g.user.municipio = (f.get("municipio") or "").strip()[:100] or None
            g.user.lembrete_ativo = bool(f.get("lembrete_ativo"))
            try:
                g.user.lembrete_dia = min(28, max(1, int(f.get("lembrete_dia", 5))))
            except ValueError:
                pass
            db.session.commit()
            flash("Perfil atualizado.", "sucesso")
            return redirect(url_for("perfil.ver"))
    return render_template("perfil.html", ativo="mais")


@bp.route("/perfil/exportar")
def exportar():
    """Todos os dados da pessoa em JSON (direito de portabilidade)."""
    u = g.user
    dados = {
        "exportado_em": datetime.now().isoformat(timespec="seconds"),
        "perfil": {"nome": u.nome, "login": u.login, "comunidade": u.comunidade,
                   "municipio": u.municipio, "criado_em": u.criado_em.isoformat(timespec="seconds")},
        "producoes": [{
            "produto": p.nome, "mes_referencia": p.referencia, "periodo": p.periodo,
            "unidade": p.rotulo, "total_produzido": p.total_produzido,
            "autoconsumo": p.autoconsumo, "trocas": p.trocas, "doacoes": p.doacoes,
            "venda": p.venda, "preco_usado": p.preco, "preco_referencia": p.preco_ref,
            "preco_ajustado": p.preco_personalizado,
            "valor_estimado": round(p.valor_total, 2),
        } for p in Produto.query.filter_by(user_id=u.id)],
        "produtos_proprios": [
            {"nome": i.nome, "unidade": i.rotulo, "preco": i.preco_unit}
            for i in ProdutoPersonalizado.query.filter_by(user_id=u.id)],
    }
    return Response(
        json.dumps(dados, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=meus-dados-renda-oculta.json"},
    )


@bp.route("/perfil/excluir", methods=["POST"])
def excluir():
    if not g.user.senha_confere(request.form.get("senha", "")):
        flash("Senha incorreta. A conta não foi excluída.", "erro")
        return redirect(url_for("perfil.ver"))
    Produto.query.filter_by(user_id=g.user.id).delete()
    ProdutoPersonalizado.query.filter_by(user_id=g.user.id).delete()
    db.session.delete(db.session.get(User, g.user.id))
    db.session.commit()
    session.clear()
    flash("Conta e dados excluídos.", "sucesso")
    return redirect(url_for("auth.entrar"))
