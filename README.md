# Renda Oculta

Calculadora do valor econômico da produção da agricultura familiar: mostra
quanto vale o que a família produz e não passa pelo caixa (autoconsumo,
trocas, doações) além da renda monetária (venda).

## Como rodar

```bash
python -m venv venv && venv\Scripts\activate      # Windows (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
python app.py                                      # http://127.0.0.1:5000
```

Na primeira vez, crie uma conta em **Criar conta**. As produções que já existiam
no banco antes do login passam para a **primeira conta criada**.

Testes: `python -m unittest discover -s tests -v`

## Estrutura

```
app.py                    ponto de entrada (python app.py)
extrair_precos.py         lê o PDF do CEASA e gera precos_ceasa.json
renda/
  __init__.py             create_app(): registra blueprints, filtros, CLI
  config.py               configurações (SECRET_KEY etc. por variável de ambiente)
  models.py               User, Tabela_Preco, ProdutoPersonalizado, Produto
  security.py             login obrigatório e proteção CSRF
  filters.py / cli.py     filtros de template e comandos de terminal
  services/               regras de negócio (sem Flask de rotas)
    calculos.py             totais, validação do registro, resumo por mês
    catalogo.py             catálogo (CEASA + produtos próprios), importação de preços
    migracao.py             atualiza bancos de versões antigas
    pdf.py                  relatório em PDF
  routes/                 uma página/assunto por arquivo (blueprints)
    main.py auth.py producao.py meus.py tabelas.py
    relatorios.py perfil.py agregado.py pwa.py
templates/  static/       interface (Bootstrap local, Chart.js, PWA)
tests/                    testes automatizados
```

## Comandos úteis

```bash
flask --app app atualizar-precos            # novo boletim: lê o PDF e troca a tabela de preços
flask --app app promover-agregador EMAIL    # libera a "Visão agregada" para um usuário
```

## Em produção

Defina `SECRET_KEY`, `SESSION_COOKIE_SECURE=1` (com HTTPS) e `MOSTRAR_LINK_RECUPERACAO=0`.
O envio de e-mail/SMS da recuperação de senha ainda precisa ser ligado
(ver `renda/routes/auth.py`, função `recuperar`).

## Requisitos funcionais

| RF | Situação |
|---|---|
| 01 Login/cadastro/recuperação | Feito (e-mail ou telefone). Recuperação mostra o link na tela; falta ligar e-mail/SMS |
| 02 Registrar produção (mês/ano) | Feito (mês/ano + frequência semanal/quinzenal/mensal) |
| 03 Validar divisão | Feito: soma dos destinos **não pode passar** do total (o PDF diz "igual") |
| 04 Catálogo | Feito (CEASA em kg/unidade/molho/espiga + unidades próprias: dúzia, caixa, saco...) |
| 05 Valor econômico | Feito |
| 06 Tela inicial | Feito (seletor de mês/acumulado) |
| 07 Tela Renda | Feito (rótulo "estimado") |
| 08 Gerenciar produções | Feito (filtros, busca, editar, excluir com confirmação) |
| 09 Dados por usuário | Feito |
| 10 Preço usado e guardado | Feito (preço da época fica no registro) |
| 11 Navegação inferior | Feito |
| 12 Gráficos | Feito |
| 13 Calendário produtivo | Feito |
| 14 Relatórios + PDF | Feito |
| 15 Perfil | Feito |
| 16 Preço por região/fonte oficial | Parcial: só CEASA-RN, atualizado com `atualizar-precos` |
| 17 Preço personalizado | Feito |
| 18 Mensagens | Feito |
| 19 Offline | Feito (fila local + sincronização ao reconectar) |
| 20 PWA | Feito |
| 21 Lembretes mensais | Parcial: aviso dentro do app (sem notificação push) |
| 22 Produtos/unidades próprios | Feito |
| 23 WhatsApp | Feito (link com resumo) |
| 24 Visão agregada | Feito (anônima; só mostra com 3+ famílias) |

## Interface

Bootstrap 5, Chart.js e a fonte ficam em `static/vendor/` (funciona sem internet).
