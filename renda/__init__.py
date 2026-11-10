"""Renda Oculta — fábrica da aplicação Flask."""

from flask import Flask, render_template

from . import cli, filters, security
from .config import Config
from .extensions import db


def create_app(config=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    db.init_app(app)
    filters.registrar(app)
    security.instalar(app)
    cli.registrar(app)

    from .routes import auth, agregado, main, meus, perfil, producao, pwa, relatorios, tabelas

    for modulo in (auth, main, producao, meus, tabelas, relatorios, perfil, agregado, pwa):
        app.register_blueprint(modulo.bp)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def erro(e):
        return render_template("erro.html", erro=e, ativo=""), e.code

    return app
