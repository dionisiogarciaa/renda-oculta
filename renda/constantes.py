"""Constantes de negócio usadas em várias partes do sistema."""

# chave -> (nome na tela, fator para converter em equivalente mensal)
PERIODOS = {
    "semanal": ("Semanal", 4),
    "quinzenal": ("Quinzenal", 2),
    "mensal": ("Mensal", 1),
}

PLURAIS = {
    "kg": "kg",
    "unidade": "unidades",
    "molho": "molhos",
    "espiga": "espigas",
    "ovo": "ovos",
    "pacote": "pacotes",
    "dúzia": "dúzias",
    "caixa": "caixas",
    "saco": "sacos",
}

# Unidades que o agricultor pode usar nos produtos próprios:
# rótulo -> medida ("kg" aceita decimais; "unidade" só inteiros)
UNIDADES_PROPRIAS = {
    "kg": "kg",
    "unidade": "unidade",
    "molho": "unidade",
    "dúzia": "unidade",
    "caixa": "unidade",
    "pacote": "unidade",
    "saco": "unidade",
}

CATEGORIA_PROPRIA = "MEUS PRODUTOS"

CAMPOS_DESTINO = ("autoconsumo", "trocas", "doacoes", "venda")

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
