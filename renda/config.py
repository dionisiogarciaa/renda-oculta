"""Configurações. Valores sensíveis vêm de variáveis de ambiente."""

import os
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///renda.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # EM PRODUÇÃO: defina SECRET_KEY (e SESSION_COOKIE_SECURE=1 com HTTPS)
    SECRET_KEY = os.environ.get("SECRET_KEY", "renda-oculta-dev")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # Sem servidor de e-mail, o link de recuperação de senha é mostrado
    # na tela (e no terminal). Em produção: desligue e envie por e-mail/SMS.
    MOSTRAR_LINK_RECUPERACAO = os.environ.get("MOSTRAR_LINK_RECUPERACAO", "1") == "1"

    JSON_PRECOS = RAIZ / "precos_ceasa.json"
    FONTE_PRECOS = "CEASA-RN (boletim diário)"
