from flask import Flask, request, redirect, url_for
import mysql.connector
from config import DB_CONFIG
from werkzeug.security import generate_password_hash
from html import escape
from decimal import Decimal, InvalidOperation

app = Flask(__name__)


# =====================================================
# CONEXAO COM O BANCO
# =====================================================

def conectar():
    return mysql.connector.connect(**DB_CONFIG)


def executar_sql(sql, parametros=()):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute(sql, parametros)
        conexao.commit()

    except mysql.connector.Error:
        if conexao and conexao.is_connected():
            conexao.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()


def consultar_sql(sql, parametros=()):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, parametros)
        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()


# =====================================================
# PAGINA HTML
# =====================================================

def pagina_html(titulo, conteudo):
    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <title>{escape(titulo)}</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                background: #f4f6f9;
                color: #222;
            }}

            h1, h2 {{
                color: #245b45;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}

            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
                overflow-wrap: anywhere;
            }}

            th {{
                background: #245b45;
                color: white;
            }}

            tr:nth-child(even) {{
                background: #eef3f0;
            }}

            input, select, textarea {{
                width: 100%;
                max-width: 550px;
                padding: 10px;
                margin-top: 5px;
                box-sizing: border-box;
            }}

            textarea {{
                min-height: 100px;
            }}

            button, .botao {{
                display: inline-block;
                background: #245b45;
                color: white;
                padding: 10px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
                margin: 8px 4px 8px 0;
            }}

            a {{
                color: #176b4d;
            }}

            .campo {{
                margin-bottom: 15px;
            }}
        </style>
    </head>

    <body>
        {conteudo}
    </body>
    </html>
    """


def listar_dados(titulo, sql, colunas):
    try:
        registros = consultar_sql(sql)

        html = f"""
        <h1>{escape(titulo)}</h1>
        <a href="/">Voltar ao início</a>
        """

        if not registros:
            html += "<p>Nenhum registro encontrado.</p>"
        else:
            html += "<table><thead><tr>"

            for rotulo, campo in colunas:
                html += f"<th>{escape(rotulo)}</th>"

            html += "</tr></thead><tbody>"

            for registro in registros:
                html += "<tr>"

                for rotulo, campo in colunas:
                    valor = registro.get(campo)
                    texto = "" if valor is None else str(valor)
                    html += f"<td>{escape(texto)}</td>"

                html += "</tr>"

            html += "</tbody></table>"

        return pagina_html(titulo, html)

    except mysql.connector.Error:
        return pagina_html(
            "Erro",
            "<h1>Erro ao consultar o banco de dados.</h1>"
        ), 500


def formulario_html(titulo, action, campos, valores=None):
    valores = valores or {}

    html = f"""
    <h1>{escape(titulo)}</h1>
    <a href="/">Voltar ao início</a>

    <form method="POST"
          action="{escape(action, quote=True)}">
    """

    for campo in campos:
        nome = campo["nome"]
        rotulo = campo["rotulo"]
        tipo = campo.get("tipo", "text")
        obrigatorio = campo.get("obrigatorio", False)
        opcoes = campo.get("opcoes", [])
        valor = valores.get(nome, campo.get("valor", ""))

        requerido = "required" if obrigatorio else ""

        html += f"""
        <div class="campo">
            <label for="{escape(nome)}">
                {escape(rotulo)}:
            </label><br>
        """

        if tipo == "textarea":
            html += f"""
            <textarea id="{escape(nome)}"
                      name="{escape(nome)}"
                      {requerido}>{escape(str(valor or ""))}</textarea>
            """

        elif tipo == "select":
            html += f"""
            <select id="{escape(nome)}"
                    name="{escape(nome)}"
                    {requerido}>
            """

            for opcao_valor, opcao_texto in opcoes:
                selecionado = (
                    "selected"
                    if str(valor) == str(opcao_valor)
                    else ""
                )

                html += (
                    f'<option value="{escape(str(opcao_valor), quote=True)}" '
                    f'{selecionado}>'
                    f'{escape(opcao_texto)}</option>'
                )

            html += "</select>"

        else:
            max_length = campo.get("maxlength")
            max_attr = (
                f'maxlength="{int(max_length)}"'
                if max_length else ""
            )

            html += f"""
            <input type="{escape(tipo, quote=True)}"
                   id="{escape(nome)}"
                   name="{escape(nome)}"
                   value="{escape(str(valor or ""), quote=True)}"
                   {max_attr}
                   {requerido}>
            """

        html += "</div>"

    html += """
        <button type="submit">Salvar cadastro</button>
    </form>
    """

    return pagina_html(titulo, html)


def erro_formulario(mensagem, codigo=400):
    return pagina_html(
        "Aviso",
        f"<h1>{escape(mensagem)}</h1><a href='/'>Voltar</a>"
    ), codigo


# =====================================================
# PAGINA INICIAL
# =====================================================

@app.route("/")
def index():
    html = """
    <h1>Sistema de Acompanhamento da Comunidade</h1>
    <p>Bem-vindo ao sistema de gestão comunitária.</p>
    <h2>Consultas e cadastros</h2>
    <ul>
    """

    links = [
        ("Usuários", "/usuarios", "/usuarios/novo"),
        ("Moradores", "/moradores", None),
        ("Setores", "/setores", "/setores/novo"),
        ("Funcionários", "/funcionarios", None),
        ("Categorias", "/categorias", "/categorias/novo"),
        ("Solicitações", "/solicitacoes", None),
        ("Histórico", "/historico", None),
        ("Produtos", "/produtos", "/produtos/novo"),
        ("Mensagens", "/mensagens", "/mensagens/novo"),
        ("Configurações", "/configuracoes",
         "/configuracoes/novo"),
    ]

    for nome, consulta, cadastro in links:
        html += f'<li><a href="{consulta}">{nome}</a>'

        if cadastro:
            html += f' | <a href="{cadastro}">Cadastrar</a>'

        html += "</li>"

    html += "</ul>"

    return pagina_html("Acompanhamento da Comunidade", html)


# =====================================================
# USUARIOS
# =====================================================

CAMPOS_USUARIO = [
    {
        "nome": "nome",
        "rotulo": "Nome",
        "obrigatorio": True,
        "maxlength": 100
    },
    {
        "nome": "login",
        "rotulo": "Login",
        "obrigatorio": True,
        "maxlength": 50
    },
    {
        "nome": "senha",
        "rotulo": "Senha",
        "tipo": "password",
        "obrigatorio": True,
        "maxlength": 255
    },
    {
        "nome": "perfil",
        "rotulo": "Perfil",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": [
            ("Morador", "Morador"),
            ("Atendente", "Atendente"),
            ("Engenheira", "Engenheira"),
            ("Administrador", "Administrador")
        ]
    }
]


@app.route("/usuarios")
def listar_usuarios():
    return listar_dados(
        "Usuários cadastrados",
        """
        SELECT id_usuario, nome, login, perfil
        FROM usuario ORDER BY id_usuario
        """,
        [
            ("ID", "id_usuario"),
            ("Nome", "nome"),
            ("Login", "login"),
            ("Perfil", "perfil")
        ]
    )


@app.route("/usuarios/novo", methods=["GET", "POST"])
def cadastrar_usuario():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar usuário",
            "/usuarios/novo",
            CAMPOS_USUARIO
        )

    nome = request.form.get("nome", "").strip()
    login = request.form.get("login", "").strip()
    senha = request.form.get("senha", "")
    perfil = request.form.get("perfil", "").strip()

    if not nome or not login or not senha or not perfil:
        return erro_formulario(
            "Preencha todos os campos obrigatórios."
        )

    if perfil not in (
        "Morador", "Atendente", "Engenheira", "Administrador"
    ):
        return erro_formulario("Perfil inválido.")

    senha_hash = generate_password_hash(senha)

    try:
        executar_sql(
            """
            INSERT INTO usuario (nome, login, senha, perfil)
            VALUES (%s, %s, %s, %s)
            """,
            (nome, login, senha_hash, perfil)
        )

        return redirect(url_for("listar_usuarios"))

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar o usuário.", 500
        )


# =====================================================
# MORADORES - LISTAGEM
# =====================================================

@app.route("/moradores")
def listar_moradores():
    return listar_dados(
        "Moradores cadastrados",
        """
        SELECT id_morador, nome, cpf, telefone, email, endereco
        FROM morador ORDER BY id_morador
        """,
        [
            ("ID", "id_morador"),
            ("Nome", "nome"),
            ("CPF", "cpf"),
            ("Telefone", "telefone"),
            ("E-mail", "email"),
            ("Endereço", "endereco")
        ]
    )


# =====================================================
# SETORES
# =====================================================

CAMPOS_SETOR = [
    {
        "nome": "nome_setor",
        "rotulo": "Nome do setor",
        "obrigatorio": True,
        "maxlength": 100
    },
    {
        "nome": "responsavel",
        "rotulo": "Responsável",
        "maxlength": 100
    }
]


@app.route("/setores")
def listar_setores():
    return listar_dados(
        "Setores cadastrados",
        """
        SELECT id_setor, nome_setor, responsavel
        FROM setor ORDER BY id_setor
        """,
        [
            ("ID", "id_setor"),
            ("Nome do setor", "nome_setor"),
            ("Responsável", "responsavel")
        ]
    )


@app.route("/setores/novo", methods=["GET", "POST"])
def cadastrar_setor():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar setor", "/setores/novo", CAMPOS_SETOR
        )

    nome = request.form.get("nome_setor", "").strip()
    responsavel = request.form.get("responsavel", "").strip()

    if not nome:
        return erro_formulario("Informe o nome do setor.")

    try:
        executar_sql(
            """
            INSERT INTO setor (nome_setor, responsavel)
            VALUES (%s, %s)
            """,
            (nome, responsavel or None)
        )

        return redirect(url_for("listar_setores"))

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar o setor.", 500
        )


# =====================================================
# FUNCIONARIOS - LISTAGEM
# =====================================================

@app.route("/funcionarios")
def listar_funcionarios():
    return listar_dados(
        "Funcionários cadastrados",
        """
        SELECT f.id_funcionario, f.nome, f.matricula,
               f.cargo, s.nome_setor AS setor
        FROM funcionario f
        INNER JOIN setor s ON f.id_setor = s.id_setor
        ORDER BY f.id_funcionario
        """,
        [
            ("ID", "id_funcionario"),
            ("Nome", "nome"),
            ("Matrícula", "matricula"),
            ("Cargo", "cargo"),
            ("Setor", "setor")
        ]
    )


# =====================================================
# CATEGORIAS
# =====================================================

CAMPOS_CATEGORIA = [
    {
        "nome": "nome_categoria",
        "rotulo": "Nome da categoria",
        "obrigatorio": True,
        "maxlength": 50
    },
    {
        "nome": "descricao",
        "rotulo": "Descrição",
        "tipo": "textarea"
    }
]


@app.route("/categorias")
def listar_categorias():
    return listar_dados(
        "Categorias cadastradas",
        """
        SELECT id_categoria, nome_categoria, descricao
        FROM categoria ORDER BY id_categoria
        """,
        [
            ("ID", "id_categoria"),
            ("Categoria", "nome_categoria"),
            ("Descrição", "descricao")
        ]
    )


@app.route("/categorias/novo", methods=["GET", "POST"])
def cadastrar_categoria():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar categoria",
            "/categorias/novo",
            CAMPOS_CATEGORIA
        )

    nome = request.form.get("nome_categoria", "").strip()
    descricao = request.form.get("descricao", "").strip()

    if not nome:
        return erro_formulario(
            "Informe o nome da categoria."
        )

    try:
        executar_sql(
            """
            INSERT INTO categoria (nome_categoria, descricao)
            VALUES (%s, %s)
            """,
            (nome, descricao or None)
        )

        return redirect(url_for("listar_categorias"))

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar a categoria.", 500
        )
# =====================================================
# SOLICITACOES - LISTAGEM E CADASTRO
# =====================================================

CAMPOS_SOLICITACAO = [
    {
        "nome": "id_morador",
        "rotulo": "Morador",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": []
    },
    {
        "nome": "id_categoria",
        "rotulo": "Categoria",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": []
    },
    {
        "nome": "id_setor",
        "rotulo": "Setor",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": []
    },
    {
        "nome": "protocolo",
        "rotulo": "Protocolo",
        "obrigatorio": True,
        "maxlength": 20
    },
    {
        "nome": "descricao",
        "rotulo": "Descrição",
        "tipo": "textarea",
        "obrigatorio": True
    },
    {
        "nome": "localizacao",
        "rotulo": "Localização",
        "obrigatorio": True,
        "maxlength": 150
    },
    {
        "nome": "data_registro",
        "rotulo": "Data do registro",
        "tipo": "date",
        "obrigatorio": True
    },
    {
        "nome": "status",
        "rotulo": "Status",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": [
            ("Recebida", "Recebida"),
            ("Em Análise", "Em Análise"),
            ("Encaminhada", "Encaminhada"),
            ("Em Execução", "Em Execução"),
            ("Concluída", "Concluída"),
            ("Cancelada", "Cancelada")
        ]
    }
]


@app.route("/solicitacoes")
def listar_solicitacoes():
    return listar_dados(
        "Solicitações da comunidade",
        """
        SELECT
            so.id_solicitacao,
            so.protocolo,
            m.nome AS morador,
            c.nome_categoria AS categoria,
            se.nome_setor AS setor,
            so.descricao,
            so.localizacao,
            so.data_registro,
            so.status
        FROM solicitacao so
        INNER JOIN morador m
            ON so.id_morador = m.id_morador
        INNER JOIN categoria c
            ON so.id_categoria = c.id_categoria
        INNER JOIN setor se
            ON so.id_setor = se.id_setor
        ORDER BY so.id_solicitacao
        """,
        [
            ("ID", "id_solicitacao"),
            ("Protocolo", "protocolo"),
            ("Morador", "morador"),
            ("Categoria", "categoria"),
            ("Setor", "setor"),
            ("Descrição", "descricao"),
            ("Localização", "localizacao"),
            ("Data", "data_registro"),
            ("Status", "status")
        ]
    )


@app.route("/solicitacoes/novo", methods=["GET", "POST"])
def cadastrar_solicitacao():
    if request.method == "GET":
        try:
            moradores = consultar_sql(
                """
                SELECT id_morador, nome
                FROM morador
                ORDER BY nome
                """
            )

            categorias = consultar_sql(
                """
                SELECT id_categoria, nome_categoria
                FROM categoria
                ORDER BY nome_categoria
                """
            )

            setores = consultar_sql(
                """
                SELECT id_setor, nome_setor
                FROM setor
                ORDER BY nome_setor
                """
            )

            campos = [dict(c) for c in CAMPOS_SOLICITACAO]

            campos[0]["opcoes"] = [
                (m["id_morador"], m["nome"])
                for m in moradores
            ]

            campos[1]["opcoes"] = [
                (c["id_categoria"], c["nome_categoria"])
                for c in categorias
            ]

            campos[2]["opcoes"] = [
                (s["id_setor"], s["nome_setor"])
                for s in setores
            ]

            return formulario_html(
                "Cadastrar solicitação",
                "/solicitacoes/novo",
                campos
            )

        except mysql.connector.Error:
            return erro_formulario(
                "Erro ao carregar moradores, categorias ou setores.",
                500
            )

    try:
        id_morador = int(
            request.form.get("id_morador", "")
        )
        id_categoria = int(
            request.form.get("id_categoria", "")
        )
        id_setor = int(
            request.form.get("id_setor", "")
        )

    except (ValueError, TypeError):
        return erro_formulario(
            "Selecione um morador, uma categoria e um setor válidos."
        )

    protocolo = request.form.get(
        "protocolo", ""
    ).strip()

    descricao = request.form.get(
        "descricao", ""
    ).strip()

    localizacao = request.form.get(
        "localizacao", ""
    ).strip()

    data_registro = request.form.get(
        "data_registro", ""
    ).strip()

    status = request.form.get(
        "status", ""
    ).strip()

    if not all([
        protocolo,
        descricao,
        localizacao,
        data_registro,
        status
    ]):
        return erro_formulario(
            "Preencha todos os campos obrigatórios."
        )

    if status not in [
        "Recebida",
        "Em Análise",
        "Encaminhada",
        "Em Execução",
        "Concluída",
        "Cancelada"
    ]:
        return erro_formulario("Status inválido.")

    try:
        executar_sql(
            """
            INSERT INTO solicitacao (
                id_morador,
                id_categoria,
                id_setor,
                protocolo,
                descricao,
                localizacao,
                data_registro,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                id_morador,
                id_categoria,
                id_setor,
                protocolo,
                descricao,
                localizacao,
                data_registro,
                status
            )
        )

        return redirect(
            url_for("listar_solicitacoes")
        )

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar a solicitação. "
            "Confira se o morador, a categoria e o setor existem.",
            500
        )
# =====================================================
# HISTORICO - LISTAGEM E CADASTRO
# =====================================================

CAMPOS_HISTORICO = [
    {
        "nome": "id_solicitacao",
        "rotulo": "Solicitação",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": []
    },
    {
        "nome": "id_funcionario",
        "rotulo": "Funcionário",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": []
    },
    {
        "nome": "status_anterior",
        "rotulo": "Status anterior",
        "obrigatorio": True,
        "maxlength": 30
    },
    {
        "nome": "novo_status",
        "rotulo": "Novo status",
        "obrigatorio": True,
        "maxlength": 30
    },
    {
        "nome": "data_alteracao",
        "rotulo": "Data da alteração",
        "tipo": "date",
        "obrigatorio": True
    },
    {
        "nome": "observacao",
        "rotulo": "Observação",
        "tipo": "textarea"
    }
]


@app.route("/historico")
def listar_historico():
    return listar_dados(
        "Histórico de alterações",
        """
        SELECT
            h.id_historico,
            so.protocolo,
            f.nome AS funcionario,
            h.status_anterior,
            h.novo_status,
            h.data_alteracao,
            h.observacao
        FROM historico h
        INNER JOIN solicitacao so
            ON h.id_solicitacao = so.id_solicitacao
        INNER JOIN funcionario f
            ON h.id_funcionario = f.id_funcionario
        ORDER BY h.id_historico
        """,
        [
            ("ID", "id_historico"),
            ("Protocolo", "protocolo"),
            ("Funcionário", "funcionario"),
            ("Status anterior", "status_anterior"),
            ("Novo status", "novo_status"),
            ("Data", "data_alteracao"),
            ("Observação", "observacao")
        ]
    )


@app.route("/historico/novo", methods=["GET", "POST"])
def cadastrar_historico():
    if request.method == "GET":
        try:
            solicitacoes = consultar_sql(
                """
                SELECT id_solicitacao, protocolo
                FROM solicitacao
                ORDER BY id_solicitacao
                """
            )

            funcionarios = consultar_sql(
                """
                SELECT id_funcionario, nome
                FROM funcionario
                ORDER BY nome
                """
            )

            campos = [dict(c) for c in CAMPOS_HISTORICO]

            campos[0]["opcoes"] = [
                (s["id_solicitacao"], s["protocolo"])
                for s in solicitacoes
            ]

            campos[1]["opcoes"] = [
                (f["id_funcionario"], f["nome"])
                for f in funcionarios
            ]

            return formulario_html(
                "Cadastrar histórico",
                "/historico/novo",
                campos
            )

        except mysql.connector.Error:
            return erro_formulario(
                "Erro ao carregar solicitações e funcionários.",
                500
            )

    try:
        id_solicitacao = int(
            request.form.get("id_solicitacao", "")
        )
        id_funcionario = int(
            request.form.get("id_funcionario", "")
        )
    except (ValueError, TypeError):
        return erro_formulario(
            "Selecione uma solicitação e um funcionário válidos."
        )

    anterior = request.form.get(
        "status_anterior", ""
    ).strip()

    novo = request.form.get(
        "novo_status", ""
    ).strip()

    data = request.form.get(
        "data_alteracao", ""
    ).strip()

    observacao = request.form.get(
        "observacao", ""
    ).strip()

    if not anterior or not novo or not data:
        return erro_formulario(
            "Preencha os campos obrigatórios."
        )

    try:
        executar_sql(
            """
            INSERT INTO historico (
                id_solicitacao,
                id_funcionario,
                status_anterior,
                novo_status,
                data_alteracao,
                observacao
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                id_solicitacao,
                id_funcionario,
                anterior,
                novo,
                data,
                observacao or None
            )
        )

        return redirect(url_for("listar_historico"))

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar o histórico. "
            "Confira se a solicitação e o funcionário existem.",
            500
        )


# =====================================================
# PRODUTOS - LISTAGEM E CADASTRO
# =====================================================

CAMPOS_PRODUTO = [
    {
        "nome": "nome",
        "rotulo": "Nome do produto",
        "obrigatorio": True,
        "maxlength": 150
    },
    {
        "nome": "descricao",
        "rotulo": "Descrição",
        "tipo": "textarea"
    },
    {
        "nome": "preco",
        "rotulo": "Preço",
        "tipo": "number",
        "obrigatorio": True,
        "valor": "0.00"
    },
    {
        "nome": "quantidade",
        "rotulo": "Quantidade",
        "tipo": "number",
        "obrigatorio": True,
        "valor": "0"
    },
    {
        "nome": "categoria",
        "rotulo": "Categoria",
        "maxlength": 100
    },
    {
        "nome": "imagem",
        "rotulo": "Caminho ou URL da imagem",
        "maxlength": 255
    },
    {
        "nome": "status",
        "rotulo": "Status",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": [
            ("ativo", "Ativo"),
            ("inativo", "Inativo")
        ]
    }
]


@app.route("/produtos")
def listar_produtos():
    return listar_dados(
        "Produtos cadastrados",
        """
        SELECT
            id,
            nome,
            descricao,
            preco,
            quantidade,
            categoria,
            status,
            data_cadastro
        FROM produtos
        ORDER BY id
        """,
        [
            ("ID", "id"),
            ("Nome", "nome"),
            ("Descrição", "descricao"),
            ("Preço", "preco"),
            ("Quantidade", "quantidade"),
            ("Categoria", "categoria"),
            ("Status", "status"),
            ("Data de cadastro", "data_cadastro")
        ]
    )


@app.route("/produtos/novo", methods=["GET", "POST"])
def cadastrar_produto():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar produto",
            "/produtos/novo",
            CAMPOS_PRODUTO
        )

    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip()
    categoria = request.form.get("categoria", "").strip()
    imagem = request.form.get("imagem", "").strip()
    status = request.form.get("status", "ativo")

    try:
        preco = Decimal(
            request.form.get("preco", "0")
        )
        quantidade = int(
            request.form.get("quantidade", "0")
        )

        if (
            not preco.is_finite()
            or preco < 0
            or quantidade < 0
        ):
            raise ValueError

    except (ValueError, InvalidOperation):
        return erro_formulario(
            "Informe um preço e uma quantidade válidos."
        )

    if not nome:
        return erro_formulario(
            "Informe o nome do produto."
        )

    if status not in ("ativo", "inativo"):
        return erro_formulario("Status inválido.")

    try:
        executar_sql(
            """
            INSERT INTO produtos (
                nome,
                descricao,
                preco,
                quantidade,
                categoria,
                imagem,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                nome,
                descricao or None,
                preco,
                quantidade,
                categoria or None,
                imagem or None,
                status
            )
        )

        return redirect(url_for("listar_produtos"))

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar o produto.",
            500
        )


# =====================================================
# MENSAGENS - LISTAGEM E CADASTRO
# =====================================================

CAMPOS_MENSAGEM = [
    {
        "nome": "nome_remetente",
        "rotulo": "Nome do remetente",
        "obrigatorio": True,
        "maxlength": 150
    },
    {
        "nome": "email_remetente",
        "rotulo": "E-mail do remetente",
        "tipo": "email",
        "maxlength": 180
    },
    {
        "nome": "assunto",
        "rotulo": "Assunto",
        "obrigatorio": True,
        "maxlength": 200
    },
    {
        "nome": "mensagem",
        "rotulo": "Mensagem",
        "tipo": "textarea",
        "obrigatorio": True
    },
    {
        "nome": "resposta",
        "rotulo": "Resposta",
        "tipo": "textarea"
    },
    {
        "nome": "status",
        "rotulo": "Status",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": [
            ("não lida", "Não lida"),
            ("lida", "Lida"),
            ("respondida", "Respondida")
        ]
    }
]


@app.route("/mensagens")
def listar_mensagens():
    return listar_dados(
        "Mensagens recebidas",
        """
        SELECT
            id,
            nome_remetente,
            email_remetente,
            assunto,
            mensagem,
            resposta,
            status,
            data_envio
        FROM mensagens
        ORDER BY data_envio DESC
        """,
        [
            ("ID", "id"),
            ("Remetente", "nome_remetente"),
            ("E-mail", "email_remetente"),
            ("Assunto", "assunto"),
            ("Mensagem", "mensagem"),
            ("Resposta", "resposta"),
            ("Status", "status"),
            ("Data", "data_envio")
        ]
    )


@app.route("/mensagens/novo", methods=["GET", "POST"])
def cadastrar_mensagem():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar mensagem",
            "/mensagens/novo",
            CAMPOS_MENSAGEM
        )

    nome = request.form.get(
        "nome_remetente", ""
    ).strip()

    email = request.form.get(
        "email_remetente", ""
    ).strip()

    assunto = request.form.get(
        "assunto", ""
    ).strip()

    mensagem = request.form.get(
        "mensagem", ""
    ).strip()

    resposta = request.form.get(
        "resposta", ""
    ).strip()

    status = request.form.get(
        "status", "não lida"
    )

    if not nome or not assunto or not mensagem:
        return erro_formulario(
            "Preencha nome, assunto e mensagem."
        )

    if status not in (
        "não lida",
        "lida",
        "respondida"
    ):
        return erro_formulario("Status inválido.")

    try:
        executar_sql(
            """
            INSERT INTO mensagens (
                nome_remetente,
                email_remetente,
                assunto,
                mensagem,
                resposta,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                nome,
                email or None,
                assunto,
                mensagem,
                resposta or None,
                status
            )
        )

        return redirect(url_for("listar_mensagens"))

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar a mensagem.",
            500
        )


# =====================================================
# CONFIGURACOES - LISTAGEM E CADASTRO
# =====================================================

CAMPOS_CONFIGURACAO = [
    {
        "nome": "nome_site",
        "rotulo": "Nome do site",
        "obrigatorio": True,
        "maxlength": 150,
        "valor": "Meu Site"
    },
    {
        "nome": "email_contato",
        "rotulo": "E-mail de contato",
        "tipo": "email",
        "maxlength": 180
    },
    {
        "nome": "telefone",
        "rotulo": "Telefone",
        "maxlength": 30
    },
    {
        "nome": "endereco",
        "rotulo": "Endereço",
        "maxlength": 255
    },
    {
        "nome": "moeda",
        "rotulo": "Moeda",
        "obrigatorio": True,
        "maxlength": 10,
        "valor": "BRL"
    },
    {
        "nome": "notificacoes_ativas",
        "rotulo": "Notificações",
        "tipo": "select",
        "obrigatorio": True,
        "opcoes": [
            ("1", "Ativadas"),
            ("0", "Desativadas")
        ]
    }
]


@app.route("/configuracoes")
def listar_configuracoes():
    return listar_dados(
        "Configurações do sistema",
        """
        SELECT
            id,
            nome_site,
            email_contato,
            telefone,
            endereco,
            moeda,
            notificacoes_ativas,
            data_atualizacao
        FROM configuracoes
        ORDER BY id
        """,
        [
            ("ID", "id"),
            ("Nome do site", "nome_site"),
            ("E-mail de contato", "email_contato"),
            ("Telefone", "telefone"),
            ("Endereço", "endereco"),
            ("Moeda", "moeda"),
            ("Notificações ativas (1 = sim)", "notificacoes_ativas"),
            ("Última atualização", "data_atualizacao")
        ]
    )


@app.route("/configuracoes/novo", methods=["GET", "POST"])
def cadastrar_configuracao():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar configuração",
            "/configuracoes/novo",
            CAMPOS_CONFIGURACAO
        )

    nome_site = request.form.get(
        "nome_site", ""
    ).strip()

    email = request.form.get(
        "email_contato", ""
    ).strip()

    telefone = request.form.get(
        "telefone", ""
    ).strip()

    endereco = request.form.get(
        "endereco", ""
    ).strip()

    moeda = request.form.get(
        "moeda", "BRL"
    ).strip()

    notificacoes = request.form.get(
        "notificacoes_ativas", "1"
    )

    if not nome_site or not moeda:
        return erro_formulario(
            "Informe o nome do site e a moeda."
        )

    if notificacoes not in ("0", "1"):
        return erro_formulario(
            "Opção de notificação inválida."
        )

    try:
        executar_sql(
            """
            INSERT INTO configuracoes (
                nome_site,
                email_contato,
                telefone,
                endereco,
                moeda,
                notificacoes_ativas
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                nome_site,
                email or None,
                telefone or None,
                endereco or None,
                moeda,
                int(notificacoes)
            )
        )

        return redirect(
            url_for("listar_configuracoes")
        )

    except mysql.connector.Error:
        return erro_formulario(
            "Não foi possível cadastrar a configuração.",
            500
        )



// rotasFK.js — rotas das tabelas com chave estrangeira:
// morador, funcionario, solicitacao, historico
//
// Uso no seu app principal (reaproveitando o pool que você já tem):
//   const rotasFK = require('./rotasFK');
//   app.use(rotasFK(pool));
//
// O pool deve ser do mysql2/promise.

const express = require('express');

module.exports = (pool) => {
  const router = express.Router();

  // Trata erros de forma central (inclusive violações de chave estrangeira)
  const wrap = (fn) => (req, res) =>
    fn(req, res).catch((err) => {
      console.error(err);
      if (err.code === 'ER_NO_REFERENCED_ROW_2')
        return res.status(400).json({ erro: 'Chave estrangeira inválida: registro referenciado não existe.' });
      if (err.code === 'ER_ROW_IS_REFERENCED_2')
        return res.status(409).json({ erro: 'Registro não pode ser removido: está sendo usado em outra tabela.' });
      if (err.code === 'ER_BAD_NULL_ERROR')
        return res.status(400).json({ erro: 'Campo obrigatório ausente.' });
      res.status(500).json({ erro: 'Erro interno do servidor.' });
    });

  /* ======================= MORADOR (FK: id_usuario) ======================= */

  router.get('/moradores', wrap(async (req, res) => {
    const [rows] = await pool.query(
      `SELECT m.*, u.login FROM morador m
       INNER JOIN usuario u ON u.id_usuario = m.id_usuario`);
    res.json(rows);
  }));

  router.get('/moradores/:id', wrap(async (req, res) => {
    const [rows] = await pool.query(
      `SELECT m.*, u.login FROM morador m
       INNER JOIN usuario u ON u.id_usuario = m.id_usuario
       WHERE m.id_morador = ?`, [req.params.id]);
    if (!rows.length) return res.status(404).json({ erro: 'Morador não encontrado.' });
    res.json(rows[0]);
  }));

  router.post('/moradores', wrap(async (req, res) => {
    const { id_usuario, nome, cpf, telefone, email, endereco } = req.body;
    const [r] = await pool.query(
      `INSERT INTO morador (id_usuario, nome, cpf, telefone, email, endereco)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [id_usuario, nome, cpf, telefone, email, endereco]);
    res.status(201).json({ id_morador: r.insertId });
  }));

  router.put('/moradores/:id', wrap(async (req, res) => {
    const { id_usuario, nome, cpf, telefone, email, endereco } = req.body;
    const [r] = await pool.query(
      `UPDATE morador SET id_usuario=?, nome=?, cpf=?, telefone=?, email=?, endereco=?
       WHERE id_morador=?`,
      [id_usuario, nome, cpf, telefone, email, endereco, req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Morador não encontrado.' });
    res.json({ mensagem: 'Morador atualizado.' });
  }));

  router.delete('/moradores/:id', wrap(async (req, res) => {
    const [r] = await pool.query('DELETE FROM morador WHERE id_morador=?', [req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Morador não encontrado.' });
    res.json({ mensagem: 'Morador removido.' });
  }));

  /* ================= FUNCIONARIO (FK: id_usuario, id_setor) ================= */

  const SQL_FUNC = `
    SELECT f.*, s.nome_setor, u.login
    FROM funcionario f
    INNER JOIN setor s ON s.id_setor = f.id_setor
    INNER JOIN usuario u ON u.id_usuario = f.id_usuario`;

  router.get('/funcionarios', wrap(async (req, res) => {
    const [rows] = await pool.query(SQL_FUNC);
    res.json(rows);
  }));

  router.get('/funcionarios/:id', wrap(async (req, res) => {
    const [rows] = await pool.query(`${SQL_FUNC} WHERE f.id_funcionario = ?`, [req.params.id]);
    if (!rows.length) return res.status(404).json({ erro: 'Funcionário não encontrado.' });
    res.json(rows[0]);
  }));

  router.post('/funcionarios', wrap(async (req, res) => {
    const { id_usuario, id_setor, nome, matricula, cargo } = req.body;
    const [r] = await pool.query(
      `INSERT INTO funcionario (id_usuario, id_setor, nome, matricula, cargo)
       VALUES (?, ?, ?, ?, ?)`,
      [id_usuario, id_setor, nome, matricula, cargo]);
    res.status(201).json({ id_funcionario: r.insertId });
  }));

  router.put('/funcionarios/:id', wrap(async (req, res) => {
    const { id_usuario, id_setor, nome, matricula, cargo } = req.body;
    const [r] = await pool.query(
      `UPDATE funcionario SET id_usuario=?, id_setor=?, nome=?, matricula=?, cargo=?
       WHERE id_funcionario=?`,
      [id_usuario, id_setor, nome, matricula, cargo, req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Funcionário não encontrado.' });
    res.json({ mensagem: 'Funcionário atualizado.' });
  }));

  router.delete('/funcionarios/:id', wrap(async (req, res) => {
    const [r] = await pool.query('DELETE FROM funcionario WHERE id_funcionario=?', [req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Funcionário não encontrado.' });
    res.json({ mensagem: 'Funcionário removido.' });
  }));

  /* ===== SOLICITACAO (FK: id_morador, id_categoria, id_setor) ===== */

  const SQL_SOL = `
    SELECT s.*, m.nome AS morador, c.nome_categoria AS categoria, st.nome_setor AS setor
    FROM solicitacao s
    INNER JOIN morador m ON m.id_morador = s.id_morador
    INNER JOIN categoria c ON c.id_categoria = s.id_categoria
    INNER JOIN setor st ON st.id_setor = s.id_setor`;

  // Filtros opcionais: ?status=Recebida&id_setor=1&id_morador=2
  router.get('/solicitacoes', wrap(async (req, res) => {
    const filtros = [], valores = [];
    for (const campo of ['status', 'id_setor', 'id_morador', 'id_categoria']) {
      if (req.query[campo]) { filtros.push(`s.${campo} = ?`); valores.push(req.query[campo]); }
    }
    const where = filtros.length ? ` WHERE ${filtros.join(' AND ')}` : '';
    const [rows] = await pool.query(`${SQL_SOL}${where} ORDER BY s.data_registro DESC`, valores);
    res.json(rows);
  }));

  router.get('/solicitacoes/protocolo/:protocolo', wrap(async (req, res) => {
    const [rows] = await pool.query(`${SQL_SOL} WHERE s.protocolo = ?`, [req.params.protocolo]);
    if (!rows.length) return res.status(404).json({ erro: 'Solicitação não encontrada.' });
    res.json(rows[0]);
  }));

  router.get('/solicitacoes/:id', wrap(async (req, res) => {
    const [rows] = await pool.query(`${SQL_SOL} WHERE s.id_solicitacao = ?`, [req.params.id]);
    if (!rows.length) return res.status(404).json({ erro: 'Solicitação não encontrada.' });
    res.json(rows[0]);
  }));

  // Histórico de uma solicitação
  router.get('/solicitacoes/:id/historico', wrap(async (req, res) => {
    const [rows] = await pool.query(
      `SELECT h.*, f.nome AS funcionario
       FROM historico h
       INNER JOIN funcionario f ON f.id_funcionario = h.id_funcionario
       WHERE h.id_solicitacao = ?
       ORDER BY h.data_alteracao, h.id_historico`, [req.params.id]);
    res.json(rows);
  }));

  router.post('/solicitacoes', wrap(async (req, res) => {
    const { id_morador, id_categoria, id_setor, descricao, localizacao } = req.body;
    const protocolo = req.body.protocolo ||
      `PROT-${new Date().getFullYear()}-${String(Date.now()).slice(-6)}`;
    const [r] = await pool.query(
      `INSERT INTO solicitacao
       (id_morador, id_categoria, id_setor, protocolo, descricao, localizacao, data_registro, status)
       VALUES (?, ?, ?, ?, ?, ?, CURDATE(), 'Recebida')`,
      [id_morador, id_categoria, id_setor, protocolo, descricao, localizacao]);
    res.status(201).json({ id_solicitacao: r.insertId, protocolo });
  }));

  router.put('/solicitacoes/:id', wrap(async (req, res) => {
    const { id_morador, id_categoria, id_setor, descricao, localizacao } = req.body;
    const [r] = await pool.query(
      `UPDATE solicitacao SET id_morador=?, id_categoria=?, id_setor=?, descricao=?, localizacao=?
       WHERE id_solicitacao=?`,
      [id_morador, id_categoria, id_setor, descricao, localizacao, req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Solicitação não encontrada.' });
    res.json({ mensagem: 'Solicitação atualizada.' });
  }));

  router.delete('/solicitacoes/:id', wrap(async (req, res) => {
    const [r] = await pool.query('DELETE FROM solicitacao WHERE id_solicitacao=?', [req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Solicitação não encontrada.' });
    res.json({ mensagem: 'Solicitação removida.' });
  }));

  /* ========== HISTORICO (FK: id_solicitacao, id_funcionario) ========== */

  const SQL_HIST = `
    SELECT h.*, s.protocolo, f.nome AS funcionario
    FROM historico h
    INNER JOIN solicitacao s ON s.id_solicitacao = h.id_solicitacao
    INNER JOIN funcionario f ON f.id_funcionario = h.id_funcionario`;

  router.get('/historico', wrap(async (req, res) => {
    const [rows] = await pool.query(`${SQL_HIST} ORDER BY h.data_alteracao DESC, h.id_historico DESC`);
    res.json(rows);
  }));

  router.get('/historico/:id', wrap(async (req, res) => {
    const [rows] = await pool.query(`${SQL_HIST} WHERE h.id_historico = ?`, [req.params.id]);
    if (!rows.length) return res.status(404).json({ erro: 'Registro de histórico não encontrado.' });
    res.json(rows[0]);
  }));

  // Registra a mudança de status e atualiza a solicitação na mesma transação
  router.post('/historico', wrap(async (req, res) => {
    const { id_solicitacao, id_funcionario, novo_status, observacao } = req.body;
    const conn = await pool.getConnection();
    try {
      await conn.beginTransaction();

      const [sol] = await conn.query(
        'SELECT status FROM solicitacao WHERE id_solicitacao = ? FOR UPDATE', [id_solicitacao]);
      if (!sol.length) {
        await conn.rollback();
        return res.status(404).json({ erro: 'Solicitação não encontrada.' });
      }

      const [r] = await conn.query(
        `INSERT INTO historico
         (id_solicitacao, id_funcionario, status_anterior, novo_status, data_alteracao, observacao)
         VALUES (?, ?, ?, ?, CURDATE(), ?)`,
        [id_solicitacao, id_funcionario, sol[0].status, novo_status, observacao]);

      await conn.query('UPDATE solicitacao SET status = ? WHERE id_solicitacao = ?',
        [novo_status, id_solicitacao]);

      await conn.commit();
      res.status(201).json({ id_historico: r.insertId, status_anterior: sol[0].status, novo_status });
    } catch (err) {
      await conn.rollback();
      throw err;
    } finally {
      conn.release();
    }
  }));

  // Apenas a observação pode ser corrigida; o histórico funciona como registro de auditoria
  router.put('/historico/:id', wrap(async (req, res) => {
    const [r] = await pool.query(
      'UPDATE historico SET observacao=? WHERE id_historico=?', [req.body.observacao, req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Registro de histórico não encontrado.' });
    res.json({ mensagem: 'Observação atualizada.' });
  }));

  router.delete('/historico/:id', wrap(async (req, res) => {
    const [r] = await pool.query('DELETE FROM historico WHERE id_historico=?', [req.params.id]);
    if (!r.affectedRows) return res.status(404).json({ erro: 'Registro de histórico não encontrado.' });
    res.json({ mensagem: 'Registro removido.' });
  }));


  return router;
};
# =====================================================
# EXECUCAO DO SISTEMA
# =====================================================

if __name__ == "__main__":
    app.run(debug=True)        