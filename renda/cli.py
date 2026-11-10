"""Comandos de terminal:  flask --app app <comando>"""

import subprocess
import sys

import click

from .extensions import db
from .models import User
from .services.catalogo import importar_precos


def registrar(app):
    @app.cli.command("atualizar-precos")
    def atualizar_precos():
        """Lê o PDF do CEASA (extrair_precos.py) e atualiza a tabela de preços."""
        subprocess.run([sys.executable, "extrair_precos.py"], check=True, cwd=app.config["JSON_PRECOS"].parent)
        click.echo(f"{importar_precos(substituir=True)} preços atualizados.")

    @app.cli.command("promover-agregador")
    @click.argument("login")
    def promover(login):
        """Dá acesso à visão agregada (cooperativa/extensionista) a um usuário."""
        user = User.query.filter_by(login=login.strip().lower()).first()
        if not user:
            raise click.ClickException("Usuário não encontrado.")
        user.papel = "agregador"
        db.session.commit()
        click.echo(f"{user.nome} agora tem acesso à visão agregada.")
