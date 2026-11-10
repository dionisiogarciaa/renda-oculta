"""Testes dos cálculos, do formulário e do isolamento entre usuários.

Rodar:   python -m unittest discover -s tests -v
"""

import re
import unittest

from renda import create_app
from renda.extensions import db
from renda.models import Produto, User
from renda.services.migracao import inicializar_banco

TOKEN = "teste-csrf"


class Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        with self.app.app_context():
            inicializar_banco()
        self.c = self.app.test_client()
        with self.c.session_transaction() as s:
            s["csrf"] = TOKEN

    @staticmethod
    def token(client):
        """O login troca o token da sessão; sempre usamos o token atual."""
        with client.session_transaction() as s:
            return s.setdefault("csrf", TOKEN)

    def post(self, url, client=None, **dados):
        client = client or self.c
        return client.post(url, data={"csrf_token": self.token(client), **dados}, follow_redirects=True)

    def cadastrar(self, client=None, login="ana@exemplo.com", nome="Ana"):
        return self.post("/cadastro", client, nome=nome, login=login, senha="senha1234",
                         senha2="senha1234", consentimento="1", municipio="Natal")

    def registrar(self, client=None, **extra):
        dados = dict(nome="MANGA ESPADA", periodo="mensal", referencia="2026-10",
                     total_produzido="100", autoconsumo="20", trocas="10", doacoes="5", venda="40")
        dados.update(extra)
        return self.post("/producao/adicionar", client, **dados)

    def producoes(self):
        with self.app.app_context():
            return Produto.query.all()


class TestAcesso(Base):
    def test_exige_login(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/entrar", r.headers["Location"])

    def test_cadastro_e_login(self):
        self.assertIn("Conta criada", self.cadastrar().get_data(as_text=True))
        self.post("/sair")
        r = self.post("/entrar", login="ANA@exemplo.com", senha="senha1234")
        self.assertIn("Visão geral", r.get_data(as_text=True))
        self.post("/sair")
        r = self.post("/entrar", login="ana@exemplo.com", senha="errada!!")
        self.assertIn("incorretos", r.get_data(as_text=True))

    def test_telefone_e_senha_curta(self):
        r = self.post("/cadastro", nome="Rosa", login="(84) 99999-1234", senha="123", senha2="123", consentimento="1")
        self.assertIn("pelo menos 8", r.get_data(as_text=True))
        r = self.cadastrar(login="(84) 99999-1234")
        self.assertIn("Conta criada", r.get_data(as_text=True))

    def test_exige_consentimento(self):
        r = self.post("/cadastro", nome="Ana", login="a@b.com", senha="senha1234", senha2="senha1234")
        self.assertIn("aceite o uso", r.get_data(as_text=True))

    def test_csrf_bloqueia_post_sem_token(self):
        r = self.c.post("/cadastro", data={"nome": "x"})
        self.assertEqual(r.status_code, 400)

    def test_recuperacao_de_senha(self):
        self.cadastrar()
        self.post("/sair")
        r = self.post("/recuperar", login="ana@exemplo.com")
        html = r.get_data(as_text=True)
        achado = re.search(r'/redefinir/[^"]+', html)
        self.assertIsNotNone(achado)
        caminho = achado.group(0)
        self.post(caminho, senha="novasenha99", senha2="novasenha99")
        r = self.post("/entrar", login="ana@exemplo.com", senha="novasenha99")
        self.assertIn("Visão geral", r.get_data(as_text=True))
        # link só vale uma vez
        r = self.post(caminho, senha="outrasenha1", senha2="outrasenha1")
        self.assertIn("já foi usado", r.get_data(as_text=True))


class TestProducao(Base):
    def setUp(self):
        super().setUp()
        self.cadastrar()

    def test_registro_valido_guarda_preco_da_epoca(self):
        self.registrar()
        (p,) = self.producoes()
        self.assertEqual(p.referencia, "2026-10")
        self.assertGreater(p.preco_unit, 0)
        self.assertEqual(p.preco_unit, p.preco_ref)
        self.assertFalse(p.preco_personalizado)
        self.assertAlmostEqual(p.valor_total, 75 * p.preco_unit, places=6)

    def test_historico_nao_muda_quando_tabela_muda(self):
        self.registrar()
        with self.app.app_context():
            from renda.models import Tabela_Preco
            Tabela_Preco.query.update({"preco_unitario": 999})
            db.session.commit()
        (p,) = self.producoes()
        self.assertLess(p.preco, 50)

    def test_soma_dos_destinos_nao_passa_do_total(self):
        r = self.registrar(total_produzido="10", autoconsumo="6", venda="5")
        self.assertIn("não pode ser maior", r.get_data(as_text=True))
        self.assertEqual(self.producoes(), [])

    def test_validacoes(self):
        for extra, msg in [
            (dict(nome="NAO EXISTE"), "Selecione um produto"),
            (dict(periodo="anual"), "período"),
            (dict(referencia="2026-13"), "mês e o ano"),
            (dict(total_produzido="0"), "total produzido"),
            (dict(autoconsumo="-1"), "números positivos"),
            (dict(venda="abc"), "números positivos"),
            (dict(preco="0"), "preço deve ser maior"),
        ]:
            with self.subTest(extra=extra):
                self.assertIn(msg, self.registrar(**extra).get_data(as_text=True))
        self.assertEqual(self.producoes(), [])

    def test_unidade_exige_inteiro(self):
        r = self.registrar(nome="ALFACE LISA", total_produzido="10.5", autoconsumo="0", trocas="0", doacoes="0", venda="1")
        self.assertIn("números inteiros", r.get_data(as_text=True))

    def test_preco_personalizado(self):
        self.registrar(preco="1,50")
        (p,) = self.producoes()
        self.assertTrue(p.preco_personalizado)
        self.assertEqual(p.preco_unit, 1.5)

    def test_editar_e_excluir(self):
        self.registrar()
        (p,) = self.producoes()
        r = self.post(f"/producao/{p.id}/editar", periodo="semanal", referencia="2026-09",
                      total_produzido="50", autoconsumo="10", trocas="0", doacoes="0", venda="40",
                      preco=str(p.preco_unit))
        self.assertIn("Produção atualizada", r.get_data(as_text=True))
        (p,) = self.producoes()
        self.assertEqual((p.total_produzido, p.periodo, p.referencia), (50, "semanal", "2026-09"))
        self.assertFalse(p.preco_personalizado)
        self.post(f"/producao/{p.id}/remover")
        self.assertEqual(self.producoes(), [])

    def test_produto_proprio(self):
        self.post("/meus-produtos/criar", nome="Queijo coalho", rotulo="kg", preco="32,50")
        self.registrar(nome="Queijo coalho", total_produzido="10", autoconsumo="2", trocas="0", doacoes="0", venda="8")
        (p,) = self.producoes()
        self.assertEqual((p.preco_unit, p.rotulo), (32.5, "kg"))

    def test_nova_producao_so_apaga_as_minhas(self):
        self.registrar()
        outro = self.app.test_client()
        with outro.session_transaction() as s:
            s["csrf"] = TOKEN
        self.cadastrar(outro, login="bia@exemplo.com", nome="Bia")
        self.registrar(outro)
        self.post("/producao/nova")
        self.assertEqual(len(self.producoes()), 1)

    def test_sincronizacao_offline(self):
        r = self.c.post("/producao/sincronizar", headers={"X-CSRF-Token": self.token(self.c)}, json={"itens": [
            dict(nome="MANGA ESPADA", periodo="mensal", total_produzido="10", venda="5"),
            dict(nome="MANGA ESPADA", periodo="mensal", total_produzido="1", venda="5"),
        ]})
        self.assertEqual([x["ok"] for x in r.get_json()["resultados"]], [True, False])
        self.assertEqual(len(self.producoes()), 1)


class TestIsolamentoEPaginas(Base):
    def setUp(self):
        super().setUp()
        self.cadastrar()
        self.registrar()
        self.outro = self.app.test_client()
        with self.outro.session_transaction() as s:
            s["csrf"] = TOKEN
        self.cadastrar(self.outro, login="bia@exemplo.com", nome="Bia")

    def test_cada_pessoa_ve_so_os_seus_dados(self):
        (p,) = self.producoes()
        self.assertNotIn('class="prod-card', self.outro.get("/producao").get_data(as_text=True))
        self.assertIn('class="prod-card', self.c.get("/producao").get_data(as_text=True))
        self.assertEqual(self.outro.get(f"/producao/{p.id}/editar").status_code, 404)
        self.assertEqual(self.post(f"/producao/{p.id}/remover", self.outro).status_code, 404)
        self.assertEqual(len(self.producoes()), 1)

    def test_filtros_e_seletor_de_mes(self):
        self.assertEqual(self.c.get("/producao?filtro=mes").status_code, 200)
        html = self.c.get("/?mes=2026-10").get_data(as_text=True)
        self.assertIn("1 produção", html)
        html = self.c.get("/?mes=2020-01").get_data(as_text=True)   # mês inválido -> acumulado
        self.assertIn("1 produção", html)

    def test_paginas_principais(self):
        for url in ["/", "/producao", "/renda", "/graficos", "/mais", "/sobre", "/tabela", "/tabela/FRUTAS",
                    "/calendario", "/relatorios", "/relatorios?mes=2026-10", "/meus-produtos", "/perfil",
                    "/manifest.webmanifest", "/sw.js", "/offline"]:
            with self.subTest(url=url):
                self.assertEqual(self.c.get(url).status_code, 200)

    def test_pdf_e_whatsapp(self):
        r = self.c.get("/relatorios/pdf?mes=2026-10")
        self.assertEqual(r.mimetype, "application/pdf")
        self.assertTrue(r.data.startswith(b"%PDF"))
        self.assertIn("wa.me", self.c.get("/relatorios").get_data(as_text=True))

    def test_agregado_exige_papel_e_anonimato(self):
        self.assertEqual(self.c.get("/agregado").status_code, 403)
        with self.app.app_context():
            u = User.query.filter_by(login="ana@exemplo.com").one()
            u.papel = "agregador"
            db.session.commit()
        html = self.c.get("/agregado").get_data(as_text=True)
        self.assertIn("só aparecem com pelo menos 3", html)      # só 1 família com dados
        self.assertNotIn("Bia", html)

    def test_exportar_e_excluir_conta(self):
        dados = self.c.get("/perfil/exportar").get_json()
        self.assertEqual(len(dados["producoes"]), 1)
        self.post("/perfil/excluir", senha="errada", client=None)
        self.assertEqual(len(self.producoes()), 1)
        self.post("/perfil/excluir", senha="senha1234")
        with self.app.app_context():
            self.assertEqual(Produto.query.count(), 0)
            self.assertIsNone(User.query.filter_by(login="ana@exemplo.com").first())


if __name__ == "__main__":
    unittest.main()
