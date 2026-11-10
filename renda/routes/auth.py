"""Cadastro, entrada, saída e recuperação de acesso (RF01)."""

import re
from datetime import datetime

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..extensions import db
from ..models import Produto, User
from ..security import destino_seguro

bp = Blueprint("auth", __name__)

MIN_SENHA = 8


def normalizar_login(texto):
    """E-mail (minúsculo) ou telefone (só dígitos). Retorna (tipo, valor) ou (None, None)."""
    t = (texto or "").strip()
    if "@" in t:
        t = t.lower()
        ok = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", t)
        return ("email", t) if ok else (None, None)
    d = re.sub(r"\D", "", t)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    return ("telefone", d) if len(d) in (10, 11) else (None, None)


def _entrar(user):
    session.clear()
    session["uid"] = user.id
    session.permanent = True


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="recuperar-senha")


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if request.method == "POST":
        tipo, login = normalizar_login(request.form.get("login"))
        user = User.query.filter_by(login=login).first() if login else None
        if user and user.senha_confere(request.form.get("senha", "")):
            _entrar(user)
            return redirect(destino_seguro(request.args.get("next")))
        flash("E-mail/telefone ou senha incorretos.", "erro")
    return render_template("auth/entrar.html", ativo="")


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        f = request.form
        nome = (f.get("nome") or "").strip()
        tipo, login = normalizar_login(f.get("login"))
        senha = f.get("senha", "")

        erro = None
        if not nome:
            erro = "Informe o seu nome."
        elif not login:
            erro = "Informe um e-mail ou telefone (com DDD) válido."
        elif len(senha) < MIN_SENHA:
            erro = f"A senha precisa ter pelo menos {MIN_SENHA} caracteres."
        elif senha != f.get("senha2"):
            erro = "As senhas não são iguais."
        elif not f.get("consentimento"):
            erro = "Para criar a conta, aceite o uso dos seus dados."
        elif User.query.filter_by(login=login).first():
            erro = "Já existe uma conta com esse e-mail/telefone."

        if erro:
            flash(erro, "erro")
        else:
            primeiro = User.query.first() is None
            user = User(
                nome=nome, login=login, tipo_login=tipo,
                comunidade=(f.get("comunidade") or "").strip() or None,
                municipio=(f.get("municipio") or "").strip() or None,
                consentimento_em=datetime.now(),
            )
            user.definir_senha(senha)
            db.session.add(user)
            db.session.flush()
            if primeiro:   # produções de antes do login passam para a primeira conta
                Produto.query.filter(Produto.user_id.is_(None)).update({"user_id": user.id})
            db.session.commit()
            _entrar(user)
            flash("Conta criada. Bem-vindo(a)!", "sucesso")
            return redirect(url_for("main.home"))

    return render_template("auth/cadastro.html", ativo="", dados=request.form)


@bp.route("/sair", methods=["POST"])
def sair():
    session.clear()
    flash("Você saiu da conta.", "sucesso")
    return redirect(url_for("auth.entrar"))


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    link = None
    if request.method == "POST":
        _, login = normalizar_login(request.form.get("login"))
        user = User.query.filter_by(login=login).first() if login else None
        if user:
            token = _serializador().dumps({"id": user.id, "h": user.senha_hash[-12:]})
            link = url_for("auth.redefinir", token=token, _external=True)
            print(f"[recuperação de acesso] {user.login}: {link}")
        flash("Se a conta existir, enviamos as instruções de recuperação.", "sucesso")
        if not current_app.config["MOSTRAR_LINK_RECUPERACAO"]:
            link = None
    return render_template("auth/recuperar.html", ativo="", link=link)


@bp.route("/redefinir/<token>", methods=["GET", "POST"])
def redefinir(token):
    try:
        dados = _serializador().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        flash("Link inválido ou vencido. Peça um novo.", "erro")
        return redirect(url_for("auth.recuperar"))

    user = db.session.get(User, dados["id"])
    if not user or user.senha_hash[-12:] != dados["h"]:   # link já usado
        flash("Esse link já foi usado. Peça um novo.", "erro")
        return redirect(url_for("auth.recuperar"))

    if request.method == "POST":
        senha = request.form.get("senha", "")
        if len(senha) < MIN_SENHA:
            flash(f"A senha precisa ter pelo menos {MIN_SENHA} caracteres.", "erro")
        elif senha != request.form.get("senha2"):
            flash("As senhas não são iguais.", "erro")
        else:
            user.definir_senha(senha)
            db.session.commit()
            flash("Senha alterada. Entre com a nova senha.", "sucesso")
            return redirect(url_for("auth.entrar"))
    return render_template("auth/redefinir.html", ativo="")
