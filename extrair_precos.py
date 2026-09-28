"""
Extrai os preços do boletim do CEASA (PDF) e gera o arquivo precos_ceasa.json.

Rode sempre que baixar um boletim novo:

    python extrair_precos.py

Cada item do JSON tem:
    nome, categoria, unidade (como vem no PDF),
    preco_min, preco_medio, preco_max, preco_kg (coluna "P. KG" do CEASA),
    medida         -> "kg" ou "unidade"  (como o agricultor mede o produto)
    rotulo         -> nome da unidade: kg, unidade, molho, espiga, ovo, pacote
    preco_unitario -> preço de 1 kg (medida = kg) ou de 1 unidade (medida = unidade)
"""

import json
import re

import pdfplumber


PDF_PATH = "cotacoes_ceasa.pdf"
JSON_PATH = "precos_ceasa.json"


# ---------------------------------------------------------------------
# GRAMÁTICA DA COLUNA "UNIDADE"
# ---------------------------------------------------------------------
# Exemplos reais do boletim: KG, CEM, CX.PLAST.25kg, CX PLAST.20KG,
# CAIXA 06KG, SCO.20KG, MOLHO 150G, BAND.30UND, PCT. 14UNDS.,
# 15KG, 500G, 500ML, 50 ESPIGAS

REGEX_UNIDADE = re.compile(
    r"(?:^|\s)("
    r"KG"
    r"|CEM"
    r"|(?:CX\.PLAST\.|CX PLAST\.|CX\.PAP\. ?|CAIXA |SCO\.|SACO |PACOTE |PCT\. "
    r"|BAND\.|BANDEJA |POTE |MOLHO )\d+\s*(?:KG|G|UNDS?\.?|ML)"
    r"|\d+\s*(?:KG|G|ML|ESPIGAS)"
    r")$",
    re.IGNORECASE,
)

REGEX_PROCEDENCIA = re.compile(r"\s+([A-Z]{2}(?:/[A-Z]{2})*'?)$")

REGEX_PRECO = re.compile(r"R\$\s*([\d.]+,\d+)")

# Cabeçalhos de categoria que aparecem no boletim
INICIO_CATEGORIAS = ("FRUTAS", "HORTALIÇAS", "HORTALICAS", "DIVERSOS")


def converter_preco(valor):
    """'1.234,50' -> 1234.5"""
    try:
        return float(valor.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def detectar_categoria(linha):
    """
    Devolve o nome da categoria se a linha for um cabeçalho de categoria.

    Trata casos como 'D I V E R S O S' (letras espaçadas) e
    'FRUTAS    BOLETIM DIÁRIO ...' (título junto do cabeçalho).
    """
    trecho = re.split(r"\s{2,}", linha.strip())[0]

    # 'D I V E R S O S' -> 'DIVERSOS'
    if re.fullmatch(r"(?:\S ){2,}\S", trecho):
        trecho = trecho.replace(" ", "")

    trecho = trecho.upper().strip()

    if trecho.startswith(INICIO_CATEGORIAS):
        return trecho

    return None


def classificar_medida(nome, unidade, preco_medio, preco_kg):
    """
    Decide se o produto é medido em kg ou em unidade.

    Retorna (medida, rotulo, preco_unitario).
    """
    u = unidade.upper().strip()

    # Cento: 100 unidades
    if u == "CEM":
        return "unidade", "unidade", round(preco_medio / 100, 4)

    # Molho: o preço já é por molho
    if u.startswith("MOLHO"):
        return "unidade", "molho", preco_medio

    # 50 ESPIGAS
    m = re.match(r"(\d+)\s*ESPIGAS", u)
    if m:
        return "unidade", "espiga", round(preco_medio / int(m.group(1)), 4)

    # BAND.30UND / BAND.12UND / PCT. 14UNDS.
    m = re.search(r"(\d+)\s*UNDS?", u)
    if m:
        qtd = int(m.group(1))

        if nome.upper().startswith("OVOS"):
            rotulo = "ovo"
        elif u.startswith("PCT"):
            rotulo = "pacote"
        else:
            rotulo = "unidade"

        return "unidade", rotulo, round(preco_medio / qtd, 4)

    # Todo o resto (KG, caixas, sacos, bandejas...) usa o preço por kg do CEASA
    return "kg", "kg", preco_kg


def extrair_linha(linha, categoria):
    """Transforma uma linha de texto do boletim em um dicionário (ou None)."""
    precos = REGEX_PRECO.findall(linha)

    if len(precos) < 4:
        return None

    # Tudo que vem antes do primeiro "R$": produto + unidade + procedência
    prefixo = linha.split("R$")[0].strip()

    proc = REGEX_PROCEDENCIA.search(prefixo)
    if proc:
        prefixo = prefixo[: proc.start()].strip()

    unidade = ""
    achou = REGEX_UNIDADE.search(prefixo)
    if achou:
        unidade = achou.group(1).strip()
        prefixo = prefixo[: achou.start(1)].strip()

    nome = prefixo

    preco_min, preco_medio, preco_max, preco_kg = (
        converter_preco(p) for p in precos[:4]
    )

    medida, rotulo, preco_unitario = classificar_medida(
        nome, unidade, preco_medio, preco_kg
    )

    return {
        "nome": nome,
        "categoria": categoria,
        "unidade": unidade,
        "preco_min": preco_min,
        "preco_medio": preco_medio,
        "preco_max": preco_max,
        "preco_kg": preco_kg,
        "medida": medida,
        "rotulo": rotulo,
        "preco_unitario": preco_unitario,
    }


def main():
    produtos = []
    categoria_atual = None
    linhas_com_preco = 0

    with pdfplumber.open(PDF_PATH) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text(layout=True) or ""

            for linha in texto.splitlines():
                if not linha.strip():
                    continue

                if len(REGEX_PRECO.findall(linha)) >= 4:
                    linhas_com_preco += 1
                    produto = extrair_linha(linha, categoria_atual)
                    if produto and produto["nome"]:
                        produtos.append(produto)
                    else:
                        print(f"AVISO: linha não interpretada: {linha.strip()}")
                    continue

                categoria = detectar_categoria(linha)
                if categoria:
                    categoria_atual = categoria

    with open(JSON_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(produtos, arquivo, ensure_ascii=False, indent=4)

    print(f"{len(produtos)} produtos extraídos ({linhas_com_preco} linhas com preço no PDF).")

    por_categoria = {}
    for p in produtos:
        por_categoria[p["categoria"]] = por_categoria.get(p["categoria"], 0) + 1
    for cat, qtd in por_categoria.items():
        print(f"  {cat}: {qtd}")

    print(f"Arquivo '{JSON_PATH}' criado com sucesso.")


if __name__ == "__main__":
    main()
