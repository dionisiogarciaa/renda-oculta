"""Sessão do usuário, proteção das rotas e CSRF."""

import secrets

from flask import abort, g, redirect, request, session, url_for

from .extensions import db
from .models import User

# Rotas que funcionam sem login; todas as outras exigem entrar.
PUBLICAS = {
    "auth.entrar", "auth.cadastro", "auth.recuperar", "auth.redefinir",
    "main.sobre", "pwa.manifest", "pwa.service_worker", "pwa.offline", "static",
}


def token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def instalar(app):
    app.jinja_env.globals["csrf_token"] = token_csrf

    @app.before_request
    def guarda():
        g.user = db.session.get(User, session["uid"]) if "uid" in session else None

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            enviado = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
            if not secrets.compare_digest(enviado, session.get("csrf", "")):
                abort(400, "Sessão expirada. Volte, recarregue a página e tente de novo.")

        if request.endpoint is None or request.endpoint in PUBLICAS:
            return
        if g.user is None:
            return redirect(url_for("auth.entrar", next=request.full_path.rstrip("?")))


def destino_seguro(destino):
    """Só aceita caminhos do próprio site (evita redirecionamento externo)."""
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return destino
    return url_for("main.home")
