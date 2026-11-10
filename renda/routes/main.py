"""Páginas principais: Início, Renda, Gráficos, Mais e Sobre."""

from flask import Blueprint, g, render_template, request

from ..services.calculos import (
    calcular_totais, meus_produtos, mes_atual, nome_mes,
    precisa_lembrar, resumo_por_mes,
)

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    todos = meus_produtos()
    resumo = resumo_por_mes(todos)

    # Seletor de mês ou acumulado (RF06)
    opcoes = sorted({m["mes"] for m in resumo} | {mes_atual()}, reverse=True)
    mes = request.args.get("mes", "acumulado")
    if mes not in opcoes:
        mes = "acumulado"

    produtos = todos if mes == "acumulado" else [p for p in todos if p.referencia == mes]
    totais = calcular_totais(produtos)

    # Valor de tudo o que foi produzido, ao preço usado (equivalente mensal)
    producao_total = sum(p.total_produzido * p.preco * p.fator_mensal for p in produtos)

    por_produto = {}
    for p in produtos:
        por_produto[p.nome] = por_produto.get(p.nome, 0) + p.valor_total * p.fator_mensal

    ordenado = sorted(por_produto.items(), key=lambda item: item[1], reverse=True)
    produtos_grafico = ordenado[:5]
    if len(ordenado) > 5:
        produtos_grafico.append(("Outros", sum(v for _, v in ordenado[5:])))

    graficos = {
        "destinos": [
            ["Autoconsumo", round(totais["total_autoconsumo"], 2)],
            ["Trocas", round(totais["total_trocas"], 2)],
            ["Doações", round(totais["total_doacoes"], 2)],
            ["Venda", round(totais["total_venda"], 2)],
        ],
        # evolução: valor de cada mês (sempre todos os meses)
        "evolucao": [[m["curto"], round(m["valor"], 2)] for m in resumo],
        "produtos": [[nome, round(valor, 2)] for nome, valor in produtos_grafico],
    }

    return render_template(
        "home.html",
        ativo="home",
        ultimas=produtos[:3],
        producao_total=producao_total,
        n_producoes=len(produtos),
        n_produtos=len(por_produto),
        graficos=graficos,
        mes=mes,
        meses=[(m, nome_mes(m)) for m in opcoes],
        lembrar=precisa_lembrar(g.user, todos),
        **totais,
    )


@bp.route("/renda")
def renda():
    totais = calcular_totais(meus_produtos())
    return render_template("renda.html", ativo="renda", **totais)


@bp.route("/graficos")
def graficos():

    produtos = meus_produtos()

    totais = calcular_totais(produtos)

    destinos = [
        ("Autoconsumo", totais["total_autoconsumo"], "var(--cor-autoconsumo)"),
        ("Trocas", totais["total_trocas"], "var(--cor-trocas)"),
        ("Doações", totais["total_doacoes"], "var(--cor-doacoes)"),
        ("Venda", totais["total_venda"], "var(--cor-venda)"),
    ]

    total = totais["renda_oculta"]

    fatias = []
    offset = 25

    for nome, valor, cor in destinos:

        pct = (valor / total * 100) if total else 0

        fatias.append({
            "nome": nome,
            "valor": valor,
            "cor": cor,
            "pct": pct,
            "offset": offset,
        })

        offset -= pct

    maior_destino = max((d[1] for d in destinos), default=0)

    # Soma por produto (um produto pode ter mais de uma produção cadastrada)
    valor_por_produto = {}

    for p in produtos:
        valor_por_produto[p.nome] = (
            valor_por_produto.get(p.nome, 0)
            + p.valor_total * p.fator_mensal
        )

    ranking = sorted(
        (
            {"nome": nome, "valor": valor}
            for nome, valor in valor_por_produto.items()
        ),
        key=lambda item: item["valor"],
        reverse=True,
    )[:8]

    maior_produto = max((r["valor"] for r in ranking), default=0)

    return render_template(
        "graficos.html",
        ativo="mais",
        total=total,
        fatias=fatias,
        maior_destino=maior_destino,
        ranking=ranking,
        maior_produto=maior_produto,
    )


@bp.route("/mais")
def mais():
    return render_template("mais.html", ativo="mais")


@bp.route("/sobre")
def sobre():
    return render_template("sobre.html", ativo="mais")
