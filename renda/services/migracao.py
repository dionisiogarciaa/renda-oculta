"""Atualiza bancos criados por versões anteriores (sem Alembic, para manter simples)."""

from sqlalchemy import inspect, text

from ..extensions import db
from ..models import Produto, Tabela_Preco
from .catalogo import referencia

COLUNAS_NOVAS_PRODUTOS = {
    "total_produzido": "FLOAT NOT NULL DEFAULT 0",
    "periodo": "VARCHAR(10) NOT NULL DEFAULT 'mensal'",
    "criado_em": "DATETIME",
    "user_id": "INTEGER",
    "referencia": "VARCHAR(7)",
    "preco_unit": "FLOAT",
    "preco_ref": "FLOAT",
    "preco_personalizado": "BOOLEAN NOT NULL DEFAULT 0",
    "rotulo_un": "VARCHAR(20)",
    "medida_un": "VARCHAR(10)",
}


def migrar_banco():
    inspetor = inspect(db.engine)
    tabelas = inspetor.get_table_names()

    # A tabela de preços é só uma cópia do JSON: se for antiga, é recriada.
    if "tabela_de_precos" in tabelas:
        colunas = {c["name"] for c in inspetor.get_columns("tabela_de_precos")}
        if "medida" not in colunas:
            Tabela_Preco.__table__.drop(db.engine)

    if "produtos" in tabelas:
        existentes = {c["name"] for c in inspetor.get_columns("produtos")}
        with db.engine.begin() as con:
            for nome, definicao in COLUNAS_NOVAS_PRODUTOS.items():
                if nome not in existentes:
                    con.execute(text(f"ALTER TABLE produtos ADD COLUMN {nome} {definicao}"))
            if "total_produzido" not in existentes:
                con.execute(text(
                    "UPDATE produtos SET total_produzido = "
                    "autoconsumo + trocas + doacoes + venda"))
            con.execute(text(
                "UPDATE produtos SET criado_em = CURRENT_TIMESTAMP WHERE criado_em IS NULL"))


def preencher_registros_antigos():
    """Produções antigas ganham mês de referência e o preço da época (RF10)."""
    for p in Produto.query.filter(
        (Produto.referencia.is_(None)) | (Produto.preco_unit.is_(None))
    ):
        if not p.referencia:
            p.referencia = p.criado_em.strftime("%Y-%m")
        if p.preco_unit is None:
            ref = referencia(p.nome)
            if ref:
                p.preco_unit = p.preco_ref = ref["preco"]
                p.rotulo_un, p.medida_un = ref["rotulo"], ref["medida"]
    db.session.commit()


def inicializar_banco():
    from .catalogo import importar_precos

    migrar_banco()
    db.create_all()
    importar_precos()
    preencher_registros_antigos()
