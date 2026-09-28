# Renda Invisível da Agricultura Familiar (protótipo)

Protótipo em Flask que estima a renda oculta da agricultura familiar
(autoconsumo, trocas solidárias, doações e comercialização informal),
usando um banco de dados SQLite para armazenar os produtos cadastrados.

## Como rodar

1. Crie um ambiente virtual (opcional, mas recomendado):
   ```
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Rode a aplicação:
   ```
   python app.py
   ```

4. Acesse no navegador:
   ```
   http://127.0.0.1:5000
   ```

O banco de dados (`renda.db`) é criado automaticamente na primeira execução.
Bancos criados por versões anteriores são atualizados automaticamente (as
produções já cadastradas são mantidas).

## Como usar

1. Informe a renda declarada (mensal).
2. Em **Adicionar produção**, escolha o produto na lista, o período da produção
   (semanal, quinzenal ou mensal) e o total produzido. A unidade muda conforme o
   produto (kg, unidades, molhos, espigas, ovos...).
3. Distribua o total entre autoconsumo, trocas, doações e venda informal
   (a soma não pode passar do total produzido).
4. A **renda oculta** é mostrada em equivalente mensal
   (semanal × 4, quinzenal × 2, mensal × 1 — ajustável em `PERIODOS` no `app.py`).
5. **Nova produção** apaga todas as produções e a renda declarada.

## Atualizando os preços do CEASA

Coloque o novo boletim como `cotacoes_ceasa.pdf` e rode:

```
python extrair_precos.py
```

Isso gera o `precos_ceasa.json`, que é importado para o banco quando a tabela de
preços está vazia (para reimportar, apague `instance/renda.db`).

## Estrutura

- `app.py` — aplicação Flask, modelos do banco (SQLAlchemy) e rotas
- `extrair_precos.py` — lê o PDF do CEASA e gera `precos_ceasa.json`
- `precos_ceasa.json` — preços extraídos (com categoria e unidade de medida)
- `templates/index.html` — página principal com formulário e resultado
- `templates/tabela*.html` — consulta à tabela de preços por categoria
- `static/style.css` — estilo básico
- `instance/renda.db` — banco de dados SQLite (gerado automaticamente)
