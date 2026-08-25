# Renda Invisível da Agricultura Familiar (protótipo)

Protótipo em Flask que estima a renda oculta da agricultura familiar
(autoconsumo, trocas solidárias, doações e comercialização informal),
usando um banco de dados SQLite para armazenar os produtos cadastrados.

## Como rodar

1. Crie um ambiente virtual (opcional, mas recomendado):
   ```
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Rode a aplicação:
   ```
   python app.py
   ```

4. Acesse no navegador:
   ```
   http://127.0.0.1:5000
   ```

O banco de dados (`renda.db`) é criado automaticamente na primeira execução.

## Estrutura

- `app.py` — aplicação Flask, modelos do banco (SQLAlchemy) e rotas
- `templates/index.html` — página única com formulário e resultado
- `static/style.css` — estilo mínimo, apenas para alinhamento e centralização
- `renda.db` — banco de dados SQLite (gerado automaticamente)
