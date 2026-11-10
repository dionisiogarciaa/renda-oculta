"""Filtros de template."""

from .constantes import PLURAIS


def registrar(app):
    @app.template_filter("plural")
    def plural(rotulo):
        return PLURAIS.get(rotulo, rotulo)

    @app.template_filter("qtd")
    def qtd(valor):
        """5.0 -> '5' | 2.5 -> '2.5'"""
        return f"{valor:.2f}".rstrip("0").rstrip(".") or "0"

    @app.template_filter("brl")
    def brl(valor):
        """1234.5 -> '1.234,50' (formato brasileiro)"""
        texto = f"{valor or 0:,.2f}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")
