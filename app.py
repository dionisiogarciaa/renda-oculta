"""
Ponto de entrada. Rode com:   python app.py

A aplicação está organizada no pacote `renda/`:
    renda/config.py       configurações
    renda/models.py       tabelas do banco
    renda/services/       regras de negócio (cálculos, catálogo, PDF, migração)
    renda/routes/         páginas, uma por assunto (blueprints)
    renda/security.py     login obrigatório e CSRF
"""

from renda import create_app
from renda.extensions import db
from renda.services.migracao import inicializar_banco

app = create_app()

# Garante tabelas, migrações e preços (também ao usar `flask --app app run`)
with app.app_context():
    inicializar_banco()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
