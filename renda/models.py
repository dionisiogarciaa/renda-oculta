"""Modelos do banco de dados (SQLAlchemy)."""

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .constantes import MESES, PERIODOS
from .extensions import db


class User(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)

    # e-mail (minúsculo) ou telefone (só dígitos)
    login = db.Column(db.String(120), unique=True, nullable=False, index=True)
    tipo_login = db.Column(db.String(10), nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    nome = db.Column(db.String(100), nullable=False)
    comunidade = db.Column(db.String(100))
    municipio = db.Column(db.String(100))

    # "agricultor" ou "agregador" (cooperativa/extensionista; ver CLI)
    papel = db.Column(db.String(20), nullable=False, default="agricultor")

    lembrete_ativo = db.Column(db.Boolean, nullable=False, default=False)
    lembrete_dia = db.Column(db.Integer, nullable=False, default=5)

    consentimento_em = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def senha_confere(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Tabela_Preco(db.Model):
    """Preços de referência (boletim do CEASA)."""

    __tablename__ = "tabela_de_precos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(60), nullable=False)
    unidade = db.Column(db.String(50), nullable=False)
    preco_min = db.Column(db.Float)
    preco_medio = db.Column(db.Float)
    preco_max = db.Column(db.Float)
    preco_kg = db.Column(db.Float, nullable=False)
    medida = db.Column(db.String(10), nullable=False, default="kg")
    rotulo = db.Column(db.String(20), nullable=False, default="kg")
    preco_unitario = db.Column(db.Float, nullable=False)


class ProdutoPersonalizado(db.Model):
    """Produto/unidade criado pelo próprio agricultor (RF22)."""

    __tablename__ = "produtos_proprios"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    medida = db.Column(db.String(10), nullable=False)   # kg | unidade
    rotulo = db.Column(db.String(20), nullable=False)   # kg, molho, dúzia...
    preco_unit = db.Column(db.Float, nullable=False)


class Produto(db.Model):
    """Uma produção registrada por um agricultor."""

    __tablename__ = "produtos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), index=True)

    nome = db.Column(db.String(100), nullable=False)

    # Mês/ano a que a produção se refere ("AAAA-MM") — RF02
    referencia = db.Column(db.String(7))

    # Frequência informada: semanal, quinzenal ou mensal
    periodo = db.Column(db.String(10), nullable=False, default="mensal")

    total_produzido = db.Column(db.Float, nullable=False, default=0)
    autoconsumo = db.Column(db.Float, nullable=False, default=0)
    trocas = db.Column(db.Float, nullable=False, default=0)
    doacoes = db.Column(db.Float, nullable=False, default=0)
    venda = db.Column(db.Float, nullable=False, default=0)

    # Preço vigente NO MOMENTO do registro (RF10). Mudanças futuras na
    # tabela do CEASA não alteram o histórico.
    preco_unit = db.Column(db.Float)
    preco_ref = db.Column(db.Float)                       # preço de referência na época
    preco_personalizado = db.Column(db.Boolean, nullable=False, default=False)  # RF17
    rotulo_un = db.Column(db.String(20))
    medida_un = db.Column(db.String(10))

    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # ---------------------------------------------------------
    # Dados vindos do registro (com plano B para registros antigos)
    # ---------------------------------------------------------

    @property
    def ref(self):
        from .services.catalogo import referencia
        return referencia(self.nome, self.user_id)

    @property
    def preco(self):
        if self.preco_unit is not None:
            return self.preco_unit
        ref = self.ref
        return ref["preco"] if ref else 0

    @property
    def rotulo(self):
        if self.rotulo_un:
            return self.rotulo_un
        ref = self.ref
        return ref["rotulo"] if ref else "kg"

    @property
    def medida(self):
        if self.medida_un:
            return self.medida_un
        ref = self.ref
        return ref["medida"] if ref else "kg"

    @property
    def periodo_nome(self):
        return PERIODOS.get(self.periodo, PERIODOS["mensal"])[0]

    @property
    def fator_mensal(self):
        return PERIODOS.get(self.periodo, PERIODOS["mensal"])[1]

    @property
    def data_cadastro(self):
        return self.criado_em.strftime("%d/%m/%Y") if self.criado_em else ""

    @property
    def referencia_nome(self):
        if not self.referencia:
            return ""
        ano, mes = self.referencia.split("-")
        return f"{MESES[int(mes) - 1]}/{ano}"

    # ---------------------------------------------------------
    # Valores estimados (quantidade x preço)
    # ---------------------------------------------------------

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
        """Soma dos quatro destinos: quanto essa produção representa."""
        return (
            self.valor_autoconsumo + self.valor_trocas
            + self.valor_doacoes + self.valor_venda
        )
