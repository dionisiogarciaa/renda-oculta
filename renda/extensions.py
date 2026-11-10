"""Extensões do Flask (criadas aqui para evitar importações circulares)."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
