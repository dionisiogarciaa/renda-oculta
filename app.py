import json
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///renda.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================================================
# TABELA DE PREÇOS DO CEASA
# =========================================================

class Tabela_Preco(db.Model):
    __tablename__ = "tabela_de_precos"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    unidade = db.Column(db.String(50), nullable=False)

    preco_min = db.Column(db.Float)
    preco_medio = db.Column(db.Float)
    preco_max = db.Column(db.Float)
    preco_kg = db.Column(db.Float, nullable=False)


# =========================================================
# PRODUTOS CADASTRADOS PELO USUÁRIO
# =========================================================

class Produto(db.Model):
    __tablename__ = "produtos"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(
        db.String(80),
        nullable=False
    )

    autoconsumo = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    trocas = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    doacoes = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    venda = db.Column(
        db.Float,
        nullable=False,
        default=0
    )


    # =====================================================
    # BUSCAR PREÇO DO CEASA
    # =====================================================

    @property
    def preco_kg(self):

        tabela = Tabela_Preco.query.filter_by(
            nome=self.nome
        ).first()

        if tabela:
            return tabela.preco_kg

        return 0


    # =====================================================
    # VALOR DO AUTOCONSUMO
    # =====================================================

    @property
    def valor_autoconsumo(self):

        return self.autoconsumo * self.preco_kg


    # =====================================================
    # VALOR DAS TROCAS
    # =====================================================

    @property
    def valor_trocas(self):

        return self.trocas * self.preco_kg


    # =====================================================
    # VALOR DAS DOAÇÕES
    # =====================================================

    @property
    def valor_doacoes(self):

        return self.doacoes * self.preco_kg


    # =====================================================
    # VALOR DA VENDA
    # =====================================================

    @property
    def valor_venda(self):

        return self.venda * self.preco_kg


# =========================================================
# CONFIGURAÇÃO
# =========================================================

class Configuracao(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    renda_declarada = db.Column(
        db.Float,
        nullable=False,
        default=0
    )


def get_config():

    config = Configuracao.query.first()

    if config is None:

        config = Configuracao(
            renda_declarada=0
        )

        db.session.add(config)
        db.session.commit()

    return config


# =========================================================
# IMPORTAR PREÇOS DO JSON
# =========================================================

def importar_precos():

    caminho_json = (
        Path(__file__).parent
        / "precos_ceasa.json"
    )

    if not caminho_json.exists():

        print(
            "Arquivo precos_ceasa.json não encontrado."
        )

        return


    with open(
        caminho_json,
        "r",
        encoding="utf-8"
    ) as arquivo:

        dados = json.load(arquivo)


    # Não importa novamente
    if Tabela_Preco.query.first():

        return


    for item in dados:

        preco = Tabela_Preco(

            nome=item["nome"],

            categoria=item["categoria"],

            unidade=item["unidade"],

            preco_min=item.get("preco_min"),

            preco_medio=item.get("preco_medio"),

            preco_max=item.get("preco_max"),

            preco_kg=item["preco_kg"]
        )

        db.session.add(preco)


    db.session.commit()

    print(
        "Preços do CEASA importados com sucesso."
    )


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

@app.route("/")
def index():

    produtos = Produto.query.all()

    config = get_config()


    # =====================================================
    # CALCULANDO OS VALORES
    # =====================================================

    total_autoconsumo = sum(
        p.valor_autoconsumo
        for p in produtos
    )

    total_trocas = sum(
        p.valor_trocas
        for p in produtos
    )

    total_doacoes = sum(
        p.valor_doacoes
        for p in produtos
    )

    total_venda = sum(
        p.valor_venda
        for p in produtos
    )


    # =====================================================
    # RENDA OCULTA
    # =====================================================

    renda_oculta = (
        total_autoconsumo
        + total_trocas
        + total_doacoes
        + total_venda
    )


    # =====================================================
    # RENDA REAL
    # =====================================================

    renda_real = (
        config.renda_declarada
        + renda_oculta
    )


    return render_template(

        "index.html",

        produtos=produtos,

        renda_declarada=(
            config.renda_declarada
        ),

        total_autoconsumo=(
            total_autoconsumo
        ),

        total_trocas=(
            total_trocas
        ),

        total_doacoes=(
            total_doacoes
        ),

        total_venda=(
            total_venda
        ),

        renda_oculta=(
            renda_oculta
        ),

        renda_real=(
            renda_real
        )
    )


# =========================================================
# ADICIONAR PRODUTO
# =========================================================

@app.route(
    "/produto/adicionar",
    methods=["POST"]
)
def adicionar_produto():

    produto = Produto(

        nome=request.form.get(
            "nome"
        ),

        autoconsumo=float(
            request.form.get(
                "autoconsumo"
            ) or 0
        ),

        trocas=float(
            request.form.get(
                "trocas"
            ) or 0
        ),

        doacoes=float(
            request.form.get(
                "doacoes"
            ) or 0
        ),

        venda=float(
            request.form.get(
                "venda"
            ) or 0
        )
    )


    db.session.add(produto)

    db.session.commit()


    return redirect(
        url_for("index")
    )


# =========================================================
# REMOVER PRODUTO
# =========================================================

@app.route(
    "/produto/remover/<int:produto_id>",
    methods=["POST"]
)
def remover_produto(produto_id):

    produto = Produto.query.get_or_404(
        produto_id
    )

    db.session.delete(produto)

    db.session.commit()


    return redirect(
        url_for("index")
    )


# =========================================================
# ATUALIZAR RENDA DECLARADA
# =========================================================

@app.route(
    "/renda-declarada",
    methods=["POST"]
)
def atualizar_renda():

    config = get_config()

    config.renda_declarada = float(
        request.form.get(
            "renda_declarada"
        ) or 0
    )

    db.session.commit()


    return redirect(
        url_for("index")
    )


# =========================================================
# PÁGINA DE CATEGORIAS
# =========================================================

@app.route("/tabela")
def tabela():

    categorias = db.session.query(
        Tabela_Preco.categoria
    ).distinct().order_by(
        Tabela_Preco.categoria
    ).all()


    categorias = [
        categoria[0]
        for categoria in categorias
    ]


    return render_template(
        "tabela.html",
        categorias=categorias
    )


# =========================================================
# TABELA DE UMA CATEGORIA
# =========================================================

@app.route("/tabela/<categoria>")
def tabela_categoria(categoria):

    produtos = Tabela_Preco.query.filter_by(
        categoria=categoria
    ).order_by(
        Tabela_Preco.nome
    ).all()


    if not produtos:

        return redirect(
            url_for("tabela")
        )


    return render_template(
        "tabela_categoria.html",
        produtos=produtos,
        categoria=categoria
    )


# =========================================================
# INICIAR A APLICAÇÃO
# =========================================================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

        importar_precos()


    app.run(
        host="0.0.0.0",
        debug=True
    )