import json
import os
import unicodedata
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///renda.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Necessária para as mensagens de aviso (flash). Em produção, use uma variável de ambiente.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "renda-oculta-dev")

db = SQLAlchemy(app)


# =========================================================
# CONSTANTES
# =========================================================

# Período da produção -> (nome exibido, multiplicador para virar renda MENSAL)
# Obs.: semana = 4 e quinzena = 2 (mês comercial). Se o professor preferir
# 52/12 ≈ 4,33 para a semana, é só trocar aqui.
PERIODOS = {
    "semanal": ("Semanal", 4),
    "quinzenal": ("Quinzenal", 2),
    "mensal": ("Mensal", 1),
}

# Rótulo da unidade de medida (singular -> plural)
PLURAIS = {
    "kg": "kg",
    "unidade": "unidades",
    "molho": "molhos",
    "espiga": "espigas",
    "ovo": "ovos",
    "pacote": "pacotes",
}


# =========================================================
# TABELA DE PREÇOS DO CEASA
# =========================================================

class Tabela_Preco(db.Model):
    __tablename__ = "tabela_de_precos"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(60), nullable=False)
    unidade = db.Column(db.String(50), nullable=False)

    preco_min = db.Column(db.Float)
    preco_medio = db.Column(db.Float)
    preco_max = db.Column(db.Float)
    preco_kg = db.Column(db.Float, nullable=False)

    # Como o agricultor mede o produto: "kg" ou "unidade"
    medida = db.Column(db.String(10), nullable=False, default="kg")

    # Nome da unidade: kg, unidade, molho, espiga, ovo, pacote
    rotulo = db.Column(db.String(20), nullable=False, default="kg")

    # Preço de 1 kg (medida = kg) ou de 1 unidade (medida = unidade)
    preco_unitario = db.Column(db.Float, nullable=False)


def _sem_acento(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).upper()


def _agrupar_por_nome(linhas):
    """
    O boletim traz alguns produtos em mais de uma embalagem
    (ex.: GOIABA em caixa de 18kg e de 25kg). Para o agricultor
    isso é um produto só, então usamos a média dos preços.
    """
    medida = linhas[0].medida
    mesmas = [l for l in linhas if l.medida == medida]

    return {
        "nome": linhas[0].nome,
        "categoria": linhas[0].categoria,
        "medida": medida,
        "rotulo": mesmas[0].rotulo,
        "preco": sum(l.preco_unitario for l in mesmas) / len(mesmas),
    }


def catalogo(categoria=None):
    """
    Lista de produtos para o dropdown (um item por nome).

    Se 'categoria' for informada, traz somente os produtos dela
    (ponto de partida para os filtros por gênero).
    """
    consulta = Tabela_Preco.query.order_by(Tabela_Preco.id)

    if categoria:
        consulta = consulta.filter_by(categoria=categoria)

    grupos = {}

    for linha in consulta:
        grupos.setdefault(linha.nome, []).append(linha)

    itens = [_agrupar_por_nome(linhas) for linhas in grupos.values()]

    # Categorias na ordem do boletim; produtos em ordem alfabética
    ordem_categorias = []
    for item in itens:
        if item["categoria"] not in ordem_categorias:
            ordem_categorias.append(item["categoria"])

    itens.sort(
        key=lambda i: (
            ordem_categorias.index(i["categoria"]),
            _sem_acento(i["nome"]),
        )
    )

    return itens


def catalogo_por_categoria(categoria=None):
    """Mesma lista, agrupada como [(categoria, [produtos])] para <optgroup>."""
    grupos = {}

    for item in catalogo(categoria):
        grupos.setdefault(item["categoria"], []).append(item)

    return list(grupos.items())


def referencia(nome):
    """Dados de preço/unidade de um produto pelo nome (ou None)."""
    linhas = Tabela_Preco.query.filter_by(nome=nome).all()

    if not linhas:
        return None

    return _agrupar_por_nome(linhas)


# =========================================================
# PRODUTOS CADASTRADOS PELO USUÁRIO
# =========================================================

class Produto(db.Model):
    __tablename__ = "produtos"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    # Total produzido no período (na unidade de medida do produto)
    total_produzido = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    # semanal, quinzenal ou mensal
    periodo = db.Column(
        db.String(10),
        nullable=False,
        default="mensal"
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
    # PREÇO E UNIDADE (VÊM DA TABELA DO CEASA)
    # =====================================================

    @property
    def ref(self):

        return referencia(self.nome)

    @property
    def preco(self):

        ref = self.ref

        return ref["preco"] if ref else 0

    @property
    def rotulo(self):

        ref = self.ref

        return ref["rotulo"] if ref else "kg"


    # =====================================================
    # PERÍODO
    # =====================================================

    @property
    def periodo_nome(self):

        return PERIODOS.get(self.periodo, PERIODOS["mensal"])[0]

    @property
    def fator_mensal(self):

        return PERIODOS.get(self.periodo, PERIODOS["mensal"])[1]


    # =====================================================
    # VALORES (NO PERÍODO INFORMADO)
    # =====================================================

    @property
    def valor_autoconsumo(self):

        return self.autoconsumo * self.preco

    @property
    def valor_trocas(self):

        return self.trocas * self.preco

    @property
    def valor_doacoes(self):

        return self.doacoes * self.preco

    @property
    def valor_venda(self):

        return self.venda * self.preco

    @property
    def valor_total(self):
        """Soma dos quatro destinos: quanto essa produção representa em renda oculta."""

        return (
            self.valor_autoconsumo
            + self.valor_trocas
            + self.valor_doacoes
            + self.valor_venda
        )


# =========================================================
# FILTROS DE TEMPLATE
# =========================================================

@app.template_filter("plural")
def filtro_plural(rotulo):

    return PLURAIS.get(rotulo, rotulo)


@app.template_filter("qtd")
def filtro_qtd(valor):
    """5.0 -> '5' | 2.5 -> '2.5'"""

    texto = f"{valor:.2f}".rstrip("0").rstrip(".")

    return texto or "0"


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
            "Arquivo precos_ceasa.json não encontrado. "
            "Rode: python extrair_precos.py"
        )

        return


    # Não importa novamente
    if Tabela_Preco.query.first():

        return


    with open(
        caminho_json,
        "r",
        encoding="utf-8"
    ) as arquivo:

        dados = json.load(arquivo)


    for item in dados:

        preco = Tabela_Preco(

            nome=item["nome"],

            categoria=item["categoria"],

            unidade=item["unidade"],

            preco_min=item.get("preco_min"),

            preco_medio=item.get("preco_medio"),

            preco_max=item.get("preco_max"),

            preco_kg=item["preco_kg"],

            # Campos novos (JSON antigo não tinha: assume kg)
            medida=item.get("medida", "kg"),

            rotulo=item.get("rotulo", "kg"),

            preco_unitario=item.get(
                "preco_unitario",
                item["preco_kg"]
            )
        )

        db.session.add(preco)


    db.session.commit()

    print(
        "Preços do CEASA importados com sucesso."
    )


# =========================================================
# ATUALIZAR BANCO ANTIGO (SEM PERDER DADOS)
# =========================================================

def migrar_banco():
    """
    Bancos criados antes desta versão não têm as colunas novas.
    - tabela_de_precos: é só uma cópia do JSON, então é recriada.
    - produtos: ganha as colunas total_produzido e periodo.
    """

    inspetor = inspect(db.engine)

    tabelas = inspetor.get_table_names()


    if "tabela_de_precos" in tabelas:

        colunas = {
            c["name"]
            for c in inspetor.get_columns("tabela_de_precos")
        }

        if "medida" not in colunas:

            Tabela_Preco.__table__.drop(db.engine)


    if "produtos" in tabelas:

        colunas = {
            c["name"]
            for c in inspetor.get_columns("produtos")
        }

        if "total_produzido" not in colunas:

            with db.engine.begin() as conexao:

                conexao.execute(text(
                    "ALTER TABLE produtos ADD COLUMN "
                    "total_produzido FLOAT NOT NULL DEFAULT 0"
                ))

                conexao.execute(text(
                    "ALTER TABLE produtos ADD COLUMN "
                    "periodo VARCHAR(10) NOT NULL DEFAULT 'mensal'"
                ))

                conexao.execute(text(
                    "UPDATE produtos SET total_produzido = "
                    "autoconsumo + trocas + doacoes + venda"
                ))


def inicializar_banco():

    migrar_banco()

    db.create_all()

    importar_precos()


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

@app.route("/")
def index():

    produtos = Produto.query.all()


    # =====================================================
    # CALCULANDO OS VALORES
    # (convertidos para equivalente MENSAL, porque cada
    #  produção pode ter um período diferente)
    # =====================================================

    total_autoconsumo = sum(
        p.valor_autoconsumo * p.fator_mensal
        for p in produtos
    )

    total_trocas = sum(
        p.valor_trocas * p.fator_mensal
        for p in produtos
    )

    total_doacoes = sum(
        p.valor_doacoes * p.fator_mensal
        for p in produtos
    )

    total_venda = sum(
        p.valor_venda * p.fator_mensal
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


    # Filtro opcional por categoria (?categoria=FRUTAS),
    # já preparado para os filtros futuros
    categoria = request.args.get("categoria")


    return render_template(

        "index.html",

        produtos=produtos,

        grupos=catalogo_por_categoria(categoria),

        periodos=PERIODOS,

        plurais=PLURAIS,

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
        )
    )


# =========================================================
# ADICIONAR PRODUTO
# =========================================================

def _ler_numero(campo):
    """Lê um número do formulário (aceita vírgula). Levanta ValueError se inválido."""

    bruto = (request.form.get(campo) or "0").strip().replace(",", ".")

    valor = float(bruto)

    if valor < 0:
        raise ValueError("negativo")

    return valor


@app.route(
    "/produto/adicionar",
    methods=["POST"]
)
def adicionar_produto():

    nome = request.form.get("nome", "")

    periodo = request.form.get("periodo", "")


    # -----------------------------------------------------
    # VALIDAÇÕES
    # -----------------------------------------------------

    ref = referencia(nome)

    if ref is None:

        flash("Selecione um produto da lista.", "erro")

        return redirect(url_for("index"))


    if periodo not in PERIODOS:

        flash("Selecione o período da produção.", "erro")

        return redirect(url_for("index"))


    try:

        total = _ler_numero("total_produzido")

        autoconsumo = _ler_numero("autoconsumo")

        trocas = _ler_numero("trocas")

        doacoes = _ler_numero("doacoes")

        venda = _ler_numero("venda")

    except ValueError:

        flash(
            "Confira os números informados "
            "(use valores maiores ou iguais a zero).",
            "erro"
        )

        return redirect(url_for("index"))


    plural = PLURAIS.get(ref["rotulo"], ref["rotulo"])


    if total <= 0:

        flash("Informe o total produzido.", "erro")

        return redirect(url_for("index"))


    # Produtos vendidos por unidade não aceitam quantidade quebrada
    if ref["medida"] == "unidade":

        if any(v != int(v) for v in (total, autoconsumo, trocas, doacoes, venda)):

            flash(
                f"{nome} é medido em {plural}: use números inteiros.",
                "erro"
            )

            return redirect(url_for("index"))


    destinado = autoconsumo + trocas + doacoes + venda

    if destinado > total + 1e-9:

        flash(
            f"A soma de autoconsumo, trocas, doações e venda "
            f"({destinado:g} {plural}) não pode ser maior que o "
            f"total produzido ({total:g} {plural}).",
            "erro"
        )

        return redirect(url_for("index"))


    # -----------------------------------------------------
    # SALVAR
    # -----------------------------------------------------

    produto = Produto(

        nome=nome,

        total_produzido=total,

        periodo=periodo,

        autoconsumo=autoconsumo,

        trocas=trocas,

        doacoes=doacoes,

        venda=venda
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

    produto = db.get_or_404(
        Produto,
        produto_id
    )

    db.session.delete(produto)

    db.session.commit()


    return redirect(
        url_for("index")
    )


# =========================================================
# NOVA PRODUÇÃO (ZERA TUDO E REINICIA)
# =========================================================

@app.route(
    "/nova-producao",
    methods=["POST"]
)
def nova_producao():

    Produto.query.delete()

    db.session.commit()


    flash("Nova produção iniciada.", "sucesso")


    return redirect(
        url_for("index")
    )


# =========================================================
# PÁGINA DE CATEGORIAS
# =========================================================

@app.route("/tabela")
def tabela():

    # Categorias na ordem em que aparecem no boletim
    categorias = []

    for (categoria,) in db.session.query(
        Tabela_Preco.categoria
    ).order_by(Tabela_Preco.id):

        if categoria not in categorias:

            categorias.append(categoria)


    return render_template(
        "tabela.html",
        categorias=categorias
    )


# =========================================================
# TABELA DE UMA CATEGORIA
# =========================================================

# <path:...> porque alguns nomes de categoria têm "/"
# (ex.: HORTALIÇAS - FOLHAS / FLORES / HASTES)

@app.route("/tabela/<path:categoria>")
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

        inicializar_banco()


    app.run(
        host="0.0.0.0",
        debug=True
    )
