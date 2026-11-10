"""Relatório em PDF (RF14)."""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

VERDE = colors.HexColor("#1f7a4d")
CLARO = colors.HexColor("#dcefe2")


def reais(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _tabela(dados, larguras):
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c4e2cd")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def gerar_pdf(user, titulo_periodo, produtos, resumo, totais):
    """Retorna um BytesIO com o PDF."""
    saida = BytesIO()
    doc = SimpleDocTemplate(saida, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title="Relatório Renda Oculta")
    estilos = getSampleStyleSheet()
    h1, h2, normal = estilos["Title"], estilos["Heading2"], estilos["BodyText"]
    h1.textColor = VERDE

    partes = [
        Paragraph("Renda Oculta — Relatório", h1),
        Paragraph(
            f"{user.nome}"
            + (f" · {user.comunidade}" if user.comunidade else "")
            + (f" · {user.municipio}" if user.municipio else ""), normal),
        Paragraph(f"Período: {titulo_periodo} · gerado em {datetime.now():%d/%m/%Y}", normal),
        Spacer(1, 12),
        Paragraph("Resumo (valores estimados)", h2),
        _tabela([
            ["Indicador", "Valor"],
            ["Valor econômico total (estimado)", reais(totais["renda_oculta"])],
            ["Renda monetária (venda)", reais(totais["total_venda"])],
            ["Autoconsumo (estimado)", reais(totais["total_autoconsumo"])],
            ["Trocas (estimado)", reais(totais["total_trocas"])],
            ["Doações (estimado)", reais(totais["total_doacoes"])],
        ], [10 * cm, 5 * cm]),
        Spacer(1, 12),
    ]

    if resumo:
        linhas = [["Mês", "Produções", "Valor econômico", "Renda monetária", "Variação"]]
        for m in resumo:
            var = "-" if m["variacao"] is None else f"{m['variacao']:+.0f}%"
            linhas.append([m["nome"], str(m["n"]), reais(m["valor"]), reais(m["venda"]), var])
        partes += [Paragraph("Comparação entre meses", h2),
                   _tabela(linhas, [3.5 * cm, 2.5 * cm, 4 * cm, 4 * cm, 2.5 * cm]), Spacer(1, 12)]

    if produtos:
        linhas = [["Produto", "Mês", "Produzido", "Preço usado", "Valor estimado"]]
        for p in produtos:
            linhas.append([
                p.nome[:34], p.referencia_nome,
                f"{p.total_produzido:g} {p.rotulo}",
                reais(p.preco) + (" *" if p.preco_personalizado else ""),
                reais(p.valor_total),
            ])
        partes += [Paragraph("Produções", h2),
                   _tabela(linhas, [5.5 * cm, 3 * cm, 2.8 * cm, 2.8 * cm, 3 * cm]),
                   Paragraph("* preço ajustado pelo agricultor.", normal)]

    partes += [Spacer(1, 14), Paragraph(
        "Autoconsumo, trocas e doações são valores <b>estimados</b> com preços de "
        "referência (CEASA-RN) e não representam dinheiro recebido. "
        "Fórmula: quantidade × preço de referência.", normal)]

    doc.build(partes)
    saida.seek(0)
    return saida
