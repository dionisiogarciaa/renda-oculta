"""Instalação no celular e uso offline (RF20, RF19)."""

from flask import Blueprint, current_app, jsonify, render_template, send_from_directory

bp = Blueprint("pwa", __name__)


@bp.route("/manifest.webmanifest")
def manifest():
    resposta = jsonify({
        "name": "Renda Oculta", "short_name": "Renda Oculta",
        "description": "O valor da sua produção, mesmo quando não vira dinheiro.",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#f1f6f2", "theme_color": "#123524", "lang": "pt-BR",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    })
    resposta.mimetype = "application/manifest+json"
    return resposta


@bp.route("/sw.js")
def service_worker():
    """Na raiz, para controlar o site inteiro."""
    resposta = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta


@bp.route("/offline")
def offline():
    return render_template("offline.html", ativo="")
