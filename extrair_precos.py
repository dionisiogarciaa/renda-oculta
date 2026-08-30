import pdfplumber
import json


pdf_path = "cotacoes_ceasa.pdf"

# Categorias existentes no boletim
categorias = {
    "FRUTAS",
    "HORTALIÇAS",
    "HORTALICAS",
    "RAÍZES",
    "RAIZES",
    "TUBÉRCULOS",
    "TUBERCULOS",
    "GRÃOS",
    "GRAOS",
    "CEREAIS",
    "LEGUMINOSAS",
    "OVOS",
    "PRODUTOS DIVERSOS"
}


def converter_preco(valor):
    """
    Transforma valores como:
    'R$ 3,50' -> 3.50
    '3,50'    -> 3.50
    """
    if not valor:
        return None

    valor = valor.replace("R$", "")
    valor = valor.replace(".", "")
    valor = valor.replace(",", ".")
    valor = valor.strip()

    try:
        return float(valor)
    except ValueError:
        return None


dados_produtos = []
categoria_atual = None


with pdfplumber.open(pdf_path) as pdf:

    for pagina in pdf.pages:

        tabelas = pagina.extract_tables()

        for tabela in tabelas:

            for linha in tabela:

                if not linha:
                    continue

                # Remove espaços e valores vazios
                linha = [
                    campo.strip() if campo else ""
                    for campo in linha
                ]

                # Ignora linhas completamente vazias
                if not any(linha):
                    continue

                primeira_coluna = linha[0].upper().strip()

                # -------------------------------------------------
                # IDENTIFICAR CATEGORIA
                # -------------------------------------------------

                if primeira_coluna in categorias:
                    categoria_atual = primeira_coluna
                    continue

                # Algumas categorias podem aparecer junto
                # com o texto do boletim
                if "FRUTAS" in primeira_coluna and len(linha) <= 2:
                    categoria_atual = "FRUTAS"
                    continue

                if "HORTALIÇAS" in primeira_coluna and len(linha) <= 2:
                    categoria_atual = "HORTALIÇAS"
                    continue

                if "HORTALICAS" in primeira_coluna and len(linha) <= 2:
                    categoria_atual = "HORTALIÇAS"
                    continue

                # -------------------------------------------------
                # IGNORAR CABEÇALHOS
                # -------------------------------------------------

                if "PRODUTO" in primeira_coluna:
                    continue

                if "BOLETIM" in primeira_coluna:
                    continue

                if "PREÇOS DE MERCADO" in primeira_coluna:
                    continue

                # -------------------------------------------------
                # VERIFICAR SE É UMA LINHA DE PRODUTO
                # -------------------------------------------------

                if len(linha) < 7:
                    continue

                nome = linha[0]

                if not nome:
                    continue

                # -------------------------------------------------
                # EXTRAIR DADOS
                # -------------------------------------------------

                produto = {
                    "nome": nome,
                    "categoria": categoria_atual,
                    "unidade": linha[1],

                    "preco_min": converter_preco(linha[3]),
                    "preco_medio": converter_preco(linha[4]),
                    "preco_max": converter_preco(linha[5]),

                    # O CEASA já fornece o preço por kg
                    "preco_kg": converter_preco(linha[6])
                }

                # Só adiciona se tiver preço por kg
                if produto["preco_kg"] is not None:
                    dados_produtos.append(produto)


# -------------------------------------------------
# SALVAR JSON
# -------------------------------------------------

with open("precos_ceasa.json", "w", encoding="utf-8") as arquivo:
    json.dump(
        dados_produtos,
        arquivo,
        ensure_ascii=False,
        indent=4
    )


print(f"{len(dados_produtos)} produtos extraídos.")

print("Arquivo 'precos_ceasa.json' criado com sucesso.")