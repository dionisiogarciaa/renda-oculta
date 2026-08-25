from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///renda.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    preco = db.Column(db.Float, nullable=False, default=0)
    autoconsumo = db.Column(db.Float, nullable=False, default=0)
    trocas = db.Column(db.Float, nullable=False, default=0)
    doacoes = db.Column(db.Float, nullable=False, default=0)
    venda = db.Column(db.Float, nullable=False, default=0)

    @property
    def valor_autoconsumo(self):
        return self.preco * self.autoconsumo

    @property
    def valor_trocas(self):
        return self.preco * self.trocas

    @property
    def valor_doacoes(self):
        return self.preco * self.doacoes

    @property
    def valor_venda(self):
        return self.preco * self.venda


class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    renda_declarada = db.Column(db.Float, nullable=False, default=0)


def get_config():
    config = Configuracao.query.first()

    if config is None:
        config = Configuracao(renda_declarada=0)
        db.session.add(config)
        db.session.commit()

    return config


@app.route("/")
def index():

    produtos = Produto.query.all()
    config = get_config()

    total_autoconsumo = sum(p.valor_autoconsumo for p in produtos)
    total_trocas = sum(p.valor_trocas for p in produtos)
    total_doacoes = sum(p.valor_doacoes for p in produtos)
    total_venda = sum(p.valor_venda for p in produtos)

    renda_oculta = (
        total_autoconsumo
        + total_trocas
        + total_doacoes
        + total_venda
    )

    renda_real = config.renda_declarada + renda_oculta

    return render_template(
        "index.html",
        produtos=produtos,
        renda_declarada=config.renda_declarada,
        total_autoconsumo=total_autoconsumo,
        total_trocas=total_trocas,
        total_doacoes=total_doacoes,
        total_venda=total_venda,
        renda_oculta=renda_oculta,
        renda_real=renda_real
    )


@app.route("/produto/adicionar", methods=["POST"])
def adicionar_produto():

    produto = Produto(
        nome=request.form.get("nome"),
        preco=float(request.form.get("preco") or 0),
        autoconsumo=float(request.form.get("autoconsumo") or 0),
        trocas=float(request.form.get("trocas") or 0),
        doacoes=float(request.form.get("doacoes") or 0),
        venda=float(request.form.get("venda") or 0)
    )

    db.session.add(produto)
    db.session.commit()

    return redirect(url_for("index"))


@app.route("/produto/remover/<int:produto_id>", methods=["POST"])
def remover_produto(produto_id):

    produto = Produto.query.get_or_404(produto_id)

    db.session.delete(produto)
    db.session.commit()

    return redirect(url_for("index"))


@app.route("/renda-declarada", methods=["POST"])
def atualizar_renda():

    config = get_config()

    config.renda_declarada = float(
        request.form.get("renda_declarada") or 0
    )

    db.session.commit()

    return redirect(url_for("index"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)