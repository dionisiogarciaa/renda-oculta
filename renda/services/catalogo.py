"""Catálogo de produtos: tabela do CEASA + produtos próprios do agricultor."""

import json
import unicodedata

from flask import current_app

from ..constantes import CATEGORIA_PROPRIA
from ..extensions import db
from ..models import ProdutoPersonalizado, Tabela_Preco


def sem_acento(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).upper()


def _agrupar_por_nome(linhas):
    """
    O boletim traz alguns produtos em mais de uma embalagem (ex.: GOIABA
    em caixa de 18kg e de 25kg). Para o agricultor é um produto só,
    então usamos a média dos preços.
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


def _item_proprio(p):
    return {
        "nome": p.nome,
        "categoria": CATEGORIA_PROPRIA,
        "medida": p.medida,
        "rotulo": p.rotulo,
        "preco": p.preco_unit,
        "proprio": True,
    }


def catalogo(categoria=None, user_id=None):
    """Lista de produtos (um item por nome). Os do agricultor vêm primeiro."""
    ceasa = Tabela_Preco.query.order_by(Tabela_Preco.id)
    if categoria and categoria != CATEGORIA_PROPRIA:
        ceasa = ceasa.filter_by(categoria=categoria)

    grupos = {}
    for linha in ceasa:
        grupos.setdefault(linha.nome, []).append(linha)
    itens = [_agrupar_por_nome(l) for l in grupos.values()]

    ordem = []
    for item in itens:
        if item["categoria"] not in ordem:
            ordem.append(item["categoria"])
    itens.sort(key=lambda i: (ordem.index(i["categoria"]), sem_acento(i["nome"])))

    proprios = []
    if user_id and categoria in (None, CATEGORIA_PROPRIA):
        proprios = sorted(
            (_item_proprio(p) for p in
             ProdutoPersonalizado.query.filter_by(user_id=user_id)),
            key=lambda i: sem_acento(i["nome"]),
        )
    nomes = {i["nome"] for i in proprios}
    return proprios + [i for i in itens if i["nome"] not in nomes]


def catalogo_por_categoria(categoria=None, user_id=None):
    """Mesma lista, agrupada como [(categoria, [produtos])] para <optgroup>."""
    grupos = {}
    for item in catalogo(categoria, user_id):
        grupos.setdefault(item["categoria"], []).append(item)
    return list(grupos.items())


def referencia(nome, user_id=None):
    """Preço/unidade de um produto pelo nome (próprio primeiro) ou None."""
    if user_id:
        proprio = ProdutoPersonalizado.query.filter_by(user_id=user_id, nome=nome).first()
        if proprio:
            return _item_proprio(proprio)
    linhas = Tabela_Preco.query.filter_by(nome=nome).all()
    return _agrupar_por_nome(linhas) if linhas else None


def importar_precos(substituir=False):
    """
    Lê o precos_ceasa.json e grava na tabela de preços.
    Sem 'substituir', só importa se a tabela estiver vazia.
    Com 'substituir' (comando atualizar-precos), troca tudo pelo boletim
    novo — o histórico não muda, pois cada produção guarda o seu preço.
    """
    caminho = current_app.config["JSON_PRECOS"]

    if not caminho.exists():
        print("Arquivo precos_ceasa.json não encontrado. Rode: python extrair_precos.py")
        return 0

    if Tabela_Preco.query.first():
        if not substituir:
            return 0
        Tabela_Preco.query.delete()

    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    for item in dados:
        db.session.add(Tabela_Preco(
            nome=item["nome"],
            categoria=item["categoria"],
            unidade=item["unidade"],
            preco_min=item.get("preco_min"),
            preco_medio=item.get("preco_medio"),
            preco_max=item.get("preco_max"),
            preco_kg=item["preco_kg"],
            medida=item.get("medida", "kg"),
            rotulo=item.get("rotulo", "kg"),
            preco_unitario=item.get("preco_unitario", item["preco_kg"]),
        ))

    db.session.commit()
    print(f"{len(dados)} preços do CEASA importados.")
    return len(dados)
