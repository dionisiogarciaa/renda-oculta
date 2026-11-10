"""Regras de negócio: totais, validação do registro, resumos por mês."""

import math
import re
from datetime import datetime

from flask import g

from ..constantes import CAMPOS_DESTINO, MESES, PERIODOS, PLURAIS
from ..models import Produto
from .catalogo import referencia


# ---------------------------------------------------------
# Consultas por usuário (RF09: cada pessoa vê só os seus)
# ---------------------------------------------------------

def meus_produtos():
    return (
        Produto.query.filter_by(user_id=g.user.id)
        .order_by(Produto.criado_em.desc(), Produto.id.desc())
        .all()
    )


def mes_atual():
    return datetime.now().strftime("%Y-%m")


def nome_mes(ym, curto=False):
    ano, mes = ym.split("-")
    return f"{mes}/{ano}" if curto else f"{MESES[int(mes) - 1]}/{ano}"


def filtrar(produtos, filtro):
    """Filtro da lista de produções: todos | mes | ano (RF08)."""
    atual = mes_atual()
    if filtro == "mes":
        return [p for p in produtos if p.referencia == atual]
    if filtro == "ano":
        return [p for p in produtos if (p.referencia or "").startswith(atual[:4])]
    return produtos


# ---------------------------------------------------------
# Totais (equivalente mensal, como antes)
# ---------------------------------------------------------

def calcular_totais(produtos):
    total_autoconsumo = sum(p.valor_autoconsumo * p.fator_mensal for p in produtos)
    total_trocas = sum(p.valor_trocas * p.fator_mensal for p in produtos)
    total_doacoes = sum(p.valor_doacoes * p.fator_mensal for p in produtos)
    total_venda = sum(p.valor_venda * p.fator_mensal for p in produtos)

    renda_oculta = total_autoconsumo + total_trocas + total_doacoes + total_venda

    def pct(valor):
        return round(valor / renda_oculta * 100) if renda_oculta else 0

    return {
        "total_autoconsumo": total_autoconsumo,
        "total_trocas": total_trocas,
        "total_doacoes": total_doacoes,
        "total_venda": total_venda,
        "renda_oculta": renda_oculta,
        "pct_autoconsumo": pct(total_autoconsumo),
        "pct_trocas": pct(total_trocas),
        "pct_doacoes": pct(total_doacoes),
        "pct_venda": pct(total_venda),
    }


def resumo_por_mes(produtos):
    """[{mes, nome, n, valor, venda}] em ordem cronológica (calendário/relatórios)."""
    meses = {}
    for p in produtos:
        if not p.referencia:
            continue
        m = meses.setdefault(p.referencia, {"mes": p.referencia, "n": 0, "valor": 0.0, "venda": 0.0, "itens": []})
        m["n"] += 1
        m["valor"] += p.valor_total * p.fator_mensal
        m["venda"] += p.valor_venda * p.fator_mensal
        m["itens"].append(p)
    resumo = [meses[k] for k in sorted(meses)]
    anterior = None
    for m in resumo:
        m["nome"] = nome_mes(m["mes"])
        m["curto"] = nome_mes(m["mes"], curto=True)
        m["variacao"] = ((m["valor"] - anterior) / anterior * 100) if anterior else None
        anterior = m["valor"]
    return resumo


def precisa_lembrar(user, produtos):
    """Lembrete mensal (RF21): ativo, já passou o dia escolhido e nada registrado no mês."""
    if not user.lembrete_ativo or datetime.now().day < user.lembrete_dia:
        return False
    return not any(p.referencia == mes_atual() for p in produtos)


# ---------------------------------------------------------
# Validação do registro (RF02, RF03, RF17) — usada no cadastro,
# na edição e na sincronização offline
# ---------------------------------------------------------

def ler_numero(valor):
    bruto = str(valor if valor not in (None, "") else "0").strip().replace(",", ".")
    numero = float(bruto)
    if numero < 0 or not math.isfinite(numero):
        raise ValueError("inválido")
    return numero


def montar_producao(dados, user_id, base=None):
    """
    Valida os dados (form ou JSON). Retorna (campos, None) ou (None, erro).
    'base' é a produção existente (edição): mantém o preço de referência da época.
    """
    nome = (dados.get("nome") or "").strip()
    ref = referencia(nome, user_id)

    if ref is None and base is not None:      # produto próprio que já foi apagado
        ref = {"nome": base.nome, "medida": base.medida, "rotulo": base.rotulo,
               "preco": base.preco_ref or base.preco}
    if ref is None:
        return None, "Selecione um produto da lista."

    periodo = dados.get("periodo", "")
    if periodo not in PERIODOS:
        return None, "Selecione o período da produção."

    mes = dados.get("referencia") or mes_atual()
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(mes)):
        return None, "Informe o mês e o ano da produção."

    try:
        total = ler_numero(dados.get("total_produzido"))
        destinos = {c: ler_numero(dados.get(c)) for c in CAMPOS_DESTINO}
        texto_preco = str(dados.get("preco") or "").strip()
        preco = ler_numero(texto_preco) if texto_preco else ref["preco"]
    except ValueError:
        return None, "Use apenas números positivos nos campos de quantidade e preço."

    plural = PLURAIS.get(ref["rotulo"], ref["rotulo"])

    if total <= 0:
        return None, "Informe o total produzido."

    if preco <= 0:
        return None, "O preço deve ser maior que zero."

    if ref["medida"] == "unidade" and any(v != int(v) for v in [total, *destinos.values()]):
        return None, f"{nome} é medido em {plural}: use números inteiros."

    destinado = sum(destinos.values())
    if destinado > total + 1e-9:
        return None, (
            "A soma de autoconsumo, trocas, doações e venda "
            f"({destinado:g} {plural}) não pode ser maior que o "
            f"total produzido ({total:g} {plural})."
        )

    preco_ref = base.preco_ref if base is not None and base.preco_ref else ref["preco"]

    return {
        "nome": nome or (base.nome if base else ""),
        "periodo": periodo,
        "referencia": mes,
        "total_produzido": total,
        **destinos,
        "preco_unit": preco,
        "preco_ref": preco_ref,
        "preco_personalizado": abs(preco - preco_ref) > 0.005,
        "rotulo_un": ref["rotulo"],
        "medida_un": ref["medida"],
    }, None
