from flask import Flask, request, redirect, url_for
import mysql.connector
from config import DB_CONFIG
from werkzeug.security import generate_password_hash
from html import escape
from decimal import Decimal, InvalidOperation
from functools import wraps

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
            h1, h2 {{ color: #245b45; }}
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
            th {{ background: #245b45; color: white; }}
            tr:nth-child(even) {{ background: #eef3f0; }}
            input, select, textarea {{
                width: 100%;
                max-width: 550px;
                padding: 10px;
                margin-top: 5px;
                box-sizing: border-box;
            }}
            textarea {{ min-height: 100px; }}
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
            a {{ color: #176b4d; }}
            .campo {{ margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        {conteudo}
    </body>
    </html>
    """


def listar_dados(titulo, sql, colunas, acoes=None):
    """acoes=("/moradores", "id_morador") mostra Cadastrar / Editar / Excluir."""
    try:
        registros = consultar_sql(sql)

        html = f"""
        <h1>{escape(titulo)}</h1>
        <a href="/">Voltar ao início</a>
        """

        if acoes:
            html += (
                f'<a class="botao" '
                f'href="{escape(acoes[0], quote=True)}/novo">+ Cadastrar</a>'
            )

        if not registros:
            html += "<p>Nenhum registro encontrado.</p>"
        else:
            html += "<table><thead><tr>"

            for rotulo, campo in colunas:
                html += f"<th>{escape(rotulo)}</th>"

            if acoes:
                html += "<th>Ações</th>"

            html += "</tr></thead><tbody>"

            for registro in registros:
                html += "<tr>"

                for rotulo, campo in colunas:
                    valor = registro.get(campo)
                    texto_celula = "" if valor is None else str(valor)
                    html += f"<td>{escape(texto_celula)}</td>"

                if acoes:
                    base = escape(acoes[0], quote=True)
                    id_registro = escape(str(registro.get(acoes[1])), quote=True)
                    html += f"""
                    <td>
                        <a href="{base}/{id_registro}/editar">Editar</a>
                        <form method="POST"
                              action="{base}/{id_registro}/excluir"
                              style="display:inline"
                              onsubmit="return confirm('Excluir este registro?');">
                            <button type="submit">Excluir</button>
                        </form>
                    </td>
                    """

                html += "</tr>"

            html += "</tbody></table>"

        return pagina_html(titulo, html), 200

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
            step = campo.get("step")
            step_attr = f'step="{escape(str(step), quote=True)}"' if step else ""

            html += f"""
            <input type="{escape(tipo, quote=True)}"
                   id="{escape(nome)}"
                   name="{escape(nome)}"
                   value="{escape(str(valor or ""), quote=True)}"
                   {max_attr}
                   {step_attr}
                   {requerido}>
            """

        html += "</div>"

    html += """
        <button type="submit">Salvar cadastro</button>
    </form>
    """

    return pagina_html(titulo, html), 200


def erro_formulario(mensagem, codigo=400):
    return pagina_html(
        "Aviso",
        f"<h1>{escape(mensagem)}</h1><a href='/'>Voltar</a>"
    ), codigo


# =====================================================
# HELPERS
# =====================================================

def tratar_erro_banco(funcao):
    """Decorator: qualquer erro do MySQL vira uma página de aviso."""
    @wraps(funcao)
    def interna(*args, **kwargs):
        try:
            return funcao(*args, **kwargs)
        except mysql.connector.Error:
            return erro_formulario("Erro ao acessar o banco de dados.", 500)
    return interna


def buscar_um(sql, parametros=()):
    registros = consultar_sql(sql, parametros)
    return registros[0] if registros else None


def opcoes_select(sql, campo_id, campo_texto, parametros=()):
    return [(r[campo_id], r[campo_texto])
            for r in consultar_sql(sql, parametros)]


def preencher_opcoes(campos, **opcoes):
    resultado = []
    for campo in campos:
        campo = dict(campo)
        if campo["nome"] in opcoes:
            campo["opcoes"] = opcoes[campo["nome"]]
        resultado.append(campo)
    return resultado


def texto(nome):
    return request.form.get(nome, "").strip()


def ler_int(nome):
    try:
        return int(request.form.get(nome, ""))
    except (ValueError, TypeError):
        return None


def mensagem_erro_banco(erro, padrao):
    conhecidos = {
        1452: "Chave estrangeira inválida: o registro relacionado não existe.",
        1451: "Não é possível excluir: o registro está sendo usado em outra tabela.",
        1062: "Já existe um registro com esses dados.",
    }
    return conhecidos.get(erro.errno, padrao), (400 if erro.errno in conhecidos else 500)


def salvar(sql, parametros, destino, padrao):
    try:
        executar_sql(sql, parametros)
        return redirect(url_for(destino))
    except mysql.connector.Error as erro:
        return erro_formulario(*mensagem_erro_banco(erro, padrao))


def excluir(tabela, chave, id_registro, destino):
    return salvar(
        f"DELETE FROM {tabela} WHERE {chave} = %s",
        (id_registro,),
        destino,
        "Não foi possível excluir o registro."
    )


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
        ("Moradores", "/moradores", "/moradores/novo"),
        ("Setores", "/setores", "/setores/novo"),
        ("Funcionários", "/funcionarios", "/funcionarios/novo"),
        ("Categorias", "/categorias", "/categorias/novo"),
        ("Solicitações", "/solicitacoes", "/solicitacoes/novo"),
        ("Histórico", "/historico", "/historico/novo"),
        ("Produtos", "/produtos", "/produtos/novo"),
        ("Mensagens", "/mensagens", "/mensagens/novo"),
        ("Configurações", "/configuracoes", "/configuracoes/novo"),
    ]

    for nome, consulta, cadastro in links:
        html += f'<li><a href="{consulta}">{nome}</a>'
        if cadastro:
            html += f' | <a href="{cadastro}">Cadastrar</a>'
        html += "</li>"

    html += "</ul>"
    return pagina_html("Acompanhamento da Comunidade", html), 200


# =====================================================
# USUARIOS
# =====================================================

CAMPOS_USUARIO = [
    {"nome": "nome", "rotulo": "Nome", "obrigatorio": True, "maxlength": 100},
    {"nome": "login", "rotulo": "Login", "obrigatorio": True, "maxlength": 50},
    {"nome": "senha", "rotulo": "Senha", "tipo": "password",
     "obrigatorio": True, "maxlength": 255},
    {"nome": "perfil", "rotulo": "Perfil", "tipo": "select",
     "obrigatorio": True,
     "opcoes": [
         ("Morador", "Morador"),
         ("Atendente", "Atendente"),
         ("Engenheira", "Engenheira"),
         ("Administrador", "Administrador"),
     ]},
]

PERFIS_VALIDOS = ("Morador", "Atendente", "Engenheira", "Administrador")


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
            ("Perfil", "perfil"),
        ],
        acoes=("/usuarios", "id_usuario")
    )


@app.route("/usuarios/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_usuario():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar usuário", "/usuarios/novo", CAMPOS_USUARIO
        )

    nome = texto("nome")
    login = texto("login")
    senha = request.form.get("senha", "")
    perfil = texto("perfil")

    if not nome or not login or not senha or not perfil:
        return erro_formulario("Preencha todos os campos obrigatórios.")

    if perfil not in PERFIS_VALIDOS:
        return erro_formulario("Perfil inválido.")

    senha_hash = generate_password_hash(senha)

    return salvar(
        """
        INSERT INTO usuario (nome, login, senha, perfil)
        VALUES (%s, %s, %s, %s)
        """,
        (nome, login, senha_hash, perfil),
        "listar_usuarios",
        "Não foi possível cadastrar o usuário."
    )


@app.route("/usuarios/<int:id_usuario>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_usuario(id_usuario):
    registro = buscar_um(
        "SELECT * FROM usuario WHERE id_usuario = %s", (id_usuario,)
    )
    if not registro:
        return erro_formulario("Usuário não encontrado.", 404)

    if request.method == "GET":
        registro_view = dict(registro)
        registro_view["senha"] = ""
        return formulario_html(
            "Editar usuário", f"/usuarios/{id_usuario}/editar",
            CAMPOS_USUARIO, registro_view
        )

    nome = texto("nome")
    login = texto("login")
    senha = request.form.get("senha", "")
    perfil = texto("perfil")

    if not nome or not login or not perfil:
        return erro_formulario("Preencha nome, login e perfil.")

    if perfil not in PERFIS_VALIDOS:
        return erro_formulario("Perfil inválido.")

    if senha:
        return salvar(
            """
            UPDATE usuario
            SET nome = %s, login = %s, senha = %s, perfil = %s
            WHERE id_usuario = %s
            """,
            (nome, login, generate_password_hash(senha), perfil, id_usuario),
            "listar_usuarios",
            "Não foi possível atualizar o usuário."
        )

    return salvar(
        """
        UPDATE usuario
        SET nome = %s, login = %s, perfil = %s
        WHERE id_usuario = %s
        """,
        (nome, login, perfil, id_usuario),
        "listar_usuarios",
        "Não foi possível atualizar o usuário."
    )


@app.route("/usuarios/<int:id_usuario>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_usuario(id_usuario):
    return excluir("usuario", "id_usuario", id_usuario, "listar_usuarios")


# =====================================================
# MORADORES
# =====================================================

CAMPOS_MORADOR = [
    {"nome": "id_usuario", "rotulo": "Usuário vinculado", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "nome", "rotulo": "Nome", "obrigatorio": True, "maxlength": 100},
    {"nome": "cpf", "rotulo": "CPF", "obrigatorio": True, "maxlength": 14},
    {"nome": "telefone", "rotulo": "Telefone", "maxlength": 20},
    {"nome": "email", "rotulo": "E-mail", "tipo": "email", "maxlength": 100},
    {"nome": "endereco", "rotulo": "Endereço", "maxlength": 150},
]


def campos_morador(id_usuario_atual=0):
    return preencher_opcoes(
        CAMPOS_MORADOR,
        id_usuario=opcoes_select(
            "SELECT id_usuario, nome FROM usuario "
            "WHERE perfil = 'Morador' OR id_usuario = %s ORDER BY nome",
            "id_usuario", "nome", (id_usuario_atual,)
        )
    )


def ler_morador():
    id_usuario = ler_int("id_usuario")
    nome, cpf = texto("nome"), texto("cpf")

    if id_usuario is None:
        return None, "Selecione um usuário válido."
    if not nome or not cpf:
        return None, "Informe o nome e o CPF."

    return (id_usuario, nome, cpf,
            texto("telefone") or None,
            texto("email") or None,
            texto("endereco") or None), None


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
            ("Endereço", "endereco"),
        ],
        acoes=("/moradores", "id_morador")
    )


@app.route("/moradores/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_morador():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar morador", "/moradores/novo", campos_morador()
        )

    dados, aviso = ler_morador()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        "INSERT INTO morador (id_usuario, nome, cpf, telefone, email, endereco) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        dados, "listar_moradores", "Não foi possível cadastrar o morador."
    )


@app.route("/moradores/<int:id_morador>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_morador(id_morador):
    registro = buscar_um(
        "SELECT * FROM morador WHERE id_morador = %s", (id_morador,)
    )
    if not registro:
        return erro_formulario("Morador não encontrado.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar morador", f"/moradores/{id_morador}/editar",
            campos_morador(registro["id_usuario"]), registro
        )

    dados, aviso = ler_morador()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        UPDATE morador
        SET id_usuario = %s, nome = %s, cpf = %s,
            telefone = %s, email = %s, endereco = %s
        WHERE id_morador = %s
        """,
        dados + (id_morador,), "listar_moradores",
        "Não foi possível atualizar o morador."
    )


@app.route("/moradores/<int:id_morador>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_morador(id_morador):
    return excluir("morador", "id_morador", id_morador, "listar_moradores")


# =====================================================
# SETORES
# =====================================================

CAMPOS_SETOR = [
    {"nome": "nome_setor", "rotulo": "Nome do setor",
     "obrigatorio": True, "maxlength": 100},
    {"nome": "responsavel", "rotulo": "Responsável", "maxlength": 100},
]


@app.route("/setores")
def listar_setores():
    return listar_dados(
        "Setores cadastrados",
        "SELECT id_setor, nome_setor, responsavel FROM setor ORDER BY id_setor",
        [
            ("ID", "id_setor"),
            ("Nome do setor", "nome_setor"),
            ("Responsável", "responsavel"),
        ],
        acoes=("/setores", "id_setor")
    )


@app.route("/setores/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_setor():
    if request.method == "GET":
        return formulario_html("Cadastrar setor", "/setores/novo", CAMPOS_SETOR)

    nome = texto("nome_setor")
    responsavel = texto("responsavel")

    if not nome:
        return erro_formulario("Informe o nome do setor.")

    return salvar(
        "INSERT INTO setor (nome_setor, responsavel) VALUES (%s, %s)",
        (nome, responsavel or None),
        "listar_setores", "Não foi possível cadastrar o setor."
    )


@app.route("/setores/<int:id_setor>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_setor(id_setor):
    registro = buscar_um(
        "SELECT * FROM setor WHERE id_setor = %s", (id_setor,)
    )
    if not registro:
        return erro_formulario("Setor não encontrado.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar setor", f"/setores/{id_setor}/editar",
            CAMPOS_SETOR, registro
        )

    nome = texto("nome_setor")
    responsavel = texto("responsavel")

    if not nome:
        return erro_formulario("Informe o nome do setor.")

    return salvar(
        "UPDATE setor SET nome_setor = %s, responsavel = %s WHERE id_setor = %s",
        (nome, responsavel or None, id_setor),
        "listar_setores", "Não foi possível atualizar o setor."
    )


@app.route("/setores/<int:id_setor>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_setor(id_setor):
    return excluir("setor", "id_setor", id_setor, "listar_setores")


# =====================================================
# FUNCIONARIOS
# =====================================================

CAMPOS_FUNCIONARIO = [
    {"nome": "id_usuario", "rotulo": "Usuário vinculado", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "id_setor", "rotulo": "Setor", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "nome", "rotulo": "Nome", "obrigatorio": True, "maxlength": 100},
    {"nome": "matricula", "rotulo": "Matrícula",
     "obrigatorio": True, "maxlength": 20},
    {"nome": "cargo", "rotulo": "Cargo", "maxlength": 50},
]


def campos_funcionario(id_usuario_atual=0):
    return preencher_opcoes(
        CAMPOS_FUNCIONARIO,
        id_usuario=opcoes_select(
            "SELECT id_usuario, nome FROM usuario "
            "WHERE perfil <> 'Morador' OR id_usuario = %s ORDER BY nome",
            "id_usuario", "nome", (id_usuario_atual,)
        ),
        id_setor=opcoes_select(
            "SELECT id_setor, nome_setor FROM setor ORDER BY nome_setor",
            "id_setor", "nome_setor"
        )
    )


def ler_funcionario():
    id_usuario, id_setor = ler_int("id_usuario"), ler_int("id_setor")
    nome, matricula = texto("nome"), texto("matricula")

    if id_usuario is None or id_setor is None:
        return None, "Selecione um usuário e um setor válidos."
    if not nome or not matricula:
        return None, "Informe o nome e a matrícula."

    return (id_usuario, id_setor, nome, matricula,
            texto("cargo") or None), None


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
            ("Setor", "setor"),
        ],
        acoes=("/funcionarios", "id_funcionario")
    )


@app.route("/funcionarios/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_funcionario():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar funcionário", "/funcionarios/novo",
            campos_funcionario()
        )

    dados, aviso = ler_funcionario()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        "INSERT INTO funcionario (id_usuario, id_setor, nome, matricula, cargo) "
        "VALUES (%s, %s, %s, %s, %s)",
        dados, "listar_funcionarios",
        "Não foi possível cadastrar o funcionário."
    )


@app.route("/funcionarios/<int:id_funcionario>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_funcionario(id_funcionario):
    registro = buscar_um(
        "SELECT * FROM funcionario WHERE id_funcionario = %s",
        (id_funcionario,)
    )
    if not registro:
        return erro_formulario("Funcionário não encontrado.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar funcionário", f"/funcionarios/{id_funcionario}/editar",
            campos_funcionario(registro["id_usuario"]), registro
        )

    dados, aviso = ler_funcionario()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        "UPDATE funcionario SET id_usuario = %s, id_setor = %s, nome = %s, "
        "matricula = %s, cargo = %s WHERE id_funcionario = %s",
        dados + (id_funcionario,), "listar_funcionarios",
        "Não foi possível atualizar o funcionário."
    )


@app.route("/funcionarios/<int:id_funcionario>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_funcionario(id_funcionario):
    return excluir("funcionario", "id_funcionario",
                   id_funcionario, "listar_funcionarios")


# =====================================================
# CATEGORIAS
# =====================================================

CAMPOS_CATEGORIA = [
    {"nome": "nome_categoria", "rotulo": "Nome da categoria",
     "obrigatorio": True, "maxlength": 50},
    {"nome": "descricao", "rotulo": "Descrição", "tipo": "textarea"},
]


@app.route("/categorias")
def listar_categorias():
    return listar_dados(
        "Categorias cadastradas",
        "SELECT id_categoria, nome_categoria, descricao "
        "FROM categoria ORDER BY id_categoria",
        [
            ("ID", "id_categoria"),
            ("Categoria", "nome_categoria"),
            ("Descrição", "descricao"),
        ],
        acoes=("/categorias", "id_categoria")
    )


@app.route("/categorias/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_categoria():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar categoria", "/categorias/novo", CAMPOS_CATEGORIA
        )

    nome = texto("nome_categoria")
    descricao = texto("descricao")

    if not nome:
        return erro_formulario("Informe o nome da categoria.")

    return salvar(
        "INSERT INTO categoria (nome_categoria, descricao) VALUES (%s, %s)",
        (nome, descricao or None),
        "listar_categorias", "Não foi possível cadastrar a categoria."
    )


@app.route("/categorias/<int:id_categoria>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_categoria(id_categoria):
    registro = buscar_um(
        "SELECT * FROM categoria WHERE id_categoria = %s", (id_categoria,)
    )
    if not registro:
        return erro_formulario("Categoria não encontrada.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar categoria", f"/categorias/{id_categoria}/editar",
            CAMPOS_CATEGORIA, registro
        )

    nome = texto("nome_categoria")
    descricao = texto("descricao")

    if not nome:
        return erro_formulario("Informe o nome da categoria.")

    return salvar(
        "UPDATE categoria SET nome_categoria = %s, descricao = %s "
        "WHERE id_categoria = %s",
        (nome, descricao or None, id_categoria),
        "listar_categorias", "Não foi possível atualizar a categoria."
    )


@app.route("/categorias/<int:id_categoria>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_categoria(id_categoria):
    return excluir("categoria", "id_categoria",
                   id_categoria, "listar_categorias")

# ===== INICIO DA PARTE 2 =====


# =====================================================
# SOLICITACOES
# =====================================================

STATUS_VALIDOS = [
    "Recebida", "Em Análise", "Encaminhada",
    "Em Execução", "Concluída", "Cancelada"
]

CAMPOS_SOLICITACAO = [
    {"nome": "id_morador", "rotulo": "Morador", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "id_categoria", "rotulo": "Categoria", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "id_setor", "rotulo": "Setor", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "protocolo", "rotulo": "Protocolo",
     "obrigatorio": True, "maxlength": 20},
    {"nome": "descricao", "rotulo": "Descrição",
     "tipo": "textarea", "obrigatorio": True},
    {"nome": "localizacao", "rotulo": "Localização",
     "obrigatorio": True, "maxlength": 150},
    {"nome": "data_registro", "rotulo": "Data do registro",
     "tipo": "date", "obrigatorio": True},
    {"nome": "status", "rotulo": "Status", "tipo": "select",
     "obrigatorio": True,
     "opcoes": [(s, s) for s in STATUS_VALIDOS]},
]


def campos_solicitacao():
    return preencher_opcoes(
        CAMPOS_SOLICITACAO,
        id_morador=opcoes_select(
            "SELECT id_morador, nome FROM morador ORDER BY nome",
            "id_morador", "nome"
        ),
        id_categoria=opcoes_select(
            "SELECT id_categoria, nome_categoria FROM categoria "
            "ORDER BY nome_categoria",
            "id_categoria", "nome_categoria"
        ),
        id_setor=opcoes_select(
            "SELECT id_setor, nome_setor FROM setor ORDER BY nome_setor",
            "id_setor", "nome_setor"
        ),
    )


def ler_solicitacao():
    ids = (ler_int("id_morador"), ler_int("id_categoria"), ler_int("id_setor"))
    if None in ids:
        return None, "Selecione um morador, uma categoria e um setor válidos."

    protocolo = texto("protocolo")
    descricao = texto("descricao")
    localizacao = texto("localizacao")
    data_registro = texto("data_registro")
    status = texto("status")

    if not all([protocolo, descricao, localizacao, data_registro, status]):
        return None, "Preencha todos os campos obrigatórios."
    if status not in STATUS_VALIDOS:
        return None, "Status inválido."

    return ids + (protocolo, descricao, localizacao, data_registro, status), None


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
        INNER JOIN morador m ON so.id_morador = m.id_morador
        INNER JOIN categoria c ON so.id_categoria = c.id_categoria
        INNER JOIN setor se ON so.id_setor = se.id_setor
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
            ("Status", "status"),
        ],
        acoes=("/solicitacoes", "id_solicitacao")
    )


@app.route("/solicitacoes/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_solicitacao():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar solicitação",
            "/solicitacoes/novo",
            campos_solicitacao()
        )

    dados, aviso = ler_solicitacao()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        INSERT INTO solicitacao (
            id_morador, id_categoria, id_setor,
            protocolo, descricao, localizacao, data_registro, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        dados, "listar_solicitacoes",
        "Não foi possível cadastrar a solicitação."
    )


@app.route("/solicitacoes/<int:id_solicitacao>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_solicitacao(id_solicitacao):
    registro = buscar_um(
        "SELECT * FROM solicitacao WHERE id_solicitacao = %s",
        (id_solicitacao,)
    )
    if not registro:
        return erro_formulario("Solicitação não encontrada.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar solicitação", f"/solicitacoes/{id_solicitacao}/editar",
            campos_solicitacao(), registro
        )

    dados, aviso = ler_solicitacao()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        UPDATE solicitacao
        SET id_morador = %s, id_categoria = %s, id_setor = %s,
            protocolo = %s, descricao = %s, localizacao = %s,
            data_registro = %s, status = %s
        WHERE id_solicitacao = %s
        """,
        dados + (id_solicitacao,), "listar_solicitacoes",
        "Não foi possível atualizar a solicitação."
    )


@app.route("/solicitacoes/<int:id_solicitacao>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_solicitacao(id_solicitacao):
    return excluir("solicitacao", "id_solicitacao",
                   id_solicitacao, "listar_solicitacoes")


# =====================================================
# HISTORICO
# =====================================================

CAMPOS_HISTORICO = [
    {"nome": "id_solicitacao", "rotulo": "Solicitação", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "id_funcionario", "rotulo": "Funcionário", "tipo": "select",
     "obrigatorio": True, "opcoes": []},
    {"nome": "status_anterior", "rotulo": "Status anterior",
     "obrigatorio": True, "maxlength": 30},
    {"nome": "novo_status", "rotulo": "Novo status",
     "obrigatorio": True, "maxlength": 30},
    {"nome": "data_alteracao", "rotulo": "Data da alteração",
     "tipo": "date", "obrigatorio": True},
    {"nome": "observacao", "rotulo": "Observação", "tipo": "textarea"},
]


def campos_historico():
    return preencher_opcoes(
        CAMPOS_HISTORICO,
        id_solicitacao=opcoes_select(
            "SELECT id_solicitacao, protocolo FROM solicitacao "
            "ORDER BY id_solicitacao",
            "id_solicitacao", "protocolo"
        ),
        id_funcionario=opcoes_select(
            "SELECT id_funcionario, nome FROM funcionario ORDER BY nome",
            "id_funcionario", "nome"
        ),
    )


def ler_historico():
    id_solicitacao = ler_int("id_solicitacao")
    id_funcionario = ler_int("id_funcionario")
    if id_solicitacao is None or id_funcionario is None:
        return None, "Selecione uma solicitação e um funcionário válidos."

    anterior = texto("status_anterior")
    novo = texto("novo_status")
    data = texto("data_alteracao")

    if not anterior or not novo or not data:
        return None, "Preencha os campos obrigatórios."

    return (id_solicitacao, id_funcionario, anterior, novo, data,
            texto("observacao") or None), None


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
        INNER JOIN solicitacao so ON h.id_solicitacao = so.id_solicitacao
        INNER JOIN funcionario f ON h.id_funcionario = f.id_funcionario
        ORDER BY h.id_historico
        """,
        [
            ("ID", "id_historico"),
            ("Protocolo", "protocolo"),
            ("Funcionário", "funcionario"),
            ("Status anterior", "status_anterior"),
            ("Novo status", "novo_status"),
            ("Data", "data_alteracao"),
            ("Observação", "observacao"),
        ],
        acoes=("/historico", "id_historico")
    )


@app.route("/historico/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_historico():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar histórico", "/historico/novo", campos_historico()
        )

    dados, aviso = ler_historico()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        INSERT INTO historico (
            id_solicitacao, id_funcionario,
            status_anterior, novo_status, data_alteracao, observacao
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        dados, "listar_historico",
        "Não foi possível cadastrar o histórico."
    )


@app.route("/historico/<int:id_historico>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_historico(id_historico):
    registro = buscar_um(
        "SELECT * FROM historico WHERE id_historico = %s", (id_historico,)
    )
    if not registro:
        return erro_formulario("Registro de histórico não encontrado.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar histórico", f"/historico/{id_historico}/editar",
            campos_historico(), registro
        )

    dados, aviso = ler_historico()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        UPDATE historico
        SET id_solicitacao = %s, id_funcionario = %s,
            status_anterior = %s, novo_status = %s,
            data_alteracao = %s, observacao = %s
        WHERE id_historico = %s
        """,
        dados + (id_historico,), "listar_historico",
        "Não foi possível atualizar o histórico."
    )


@app.route("/historico/<int:id_historico>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_historico(id_historico):
    return excluir("historico", "id_historico",
                   id_historico, "listar_historico")


# ===== FIM DA PARTE 2 =====# ===== INICIO DA PARTE 3 =====


# =====================================================
# PRODUTOS
# =====================================================

CAMPOS_PRODUTO = [
    {"nome": "nome", "rotulo": "Nome do produto",
     "obrigatorio": True, "maxlength": 150},
    {"nome": "descricao", "rotulo": "Descrição", "tipo": "textarea"},
    {"nome": "preco", "rotulo": "Preço", "tipo": "number",
     "obrigatorio": True, "valor": "0.00", "step": "0.01"},
    {"nome": "quantidade", "rotulo": "Quantidade", "tipo": "number",
     "obrigatorio": True, "valor": "0", "step": "1"},
    {"nome": "categoria", "rotulo": "Categoria", "maxlength": 100},
    {"nome": "imagem", "rotulo": "Caminho ou URL da imagem",
     "maxlength": 255},
    {"nome": "status", "rotulo": "Status", "tipo": "select",
     "obrigatorio": True,
     "opcoes": [("ativo", "Ativo"), ("inativo", "Inativo")]},
]


def ler_produto():
    nome = texto("nome")
    if not nome:
        return None, "Informe o nome do produto."

    try:
        preco = Decimal(request.form.get("preco", "0"))
        quantidade = int(request.form.get("quantidade", "0"))
        if not preco.is_finite() or preco < 0 or quantidade < 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        return None, "Informe um preço e uma quantidade válidos."

    status = texto("status") or "ativo"
    if status not in ("ativo", "inativo"):
        return None, "Status inválido."

    return (
        nome,
        texto("descricao") or None,
        preco,
        quantidade,
        texto("categoria") or None,
        texto("imagem") or None,
        status,
    ), None


@app.route("/produtos")
def listar_produtos():
    return listar_dados(
        "Produtos cadastrados",
        """
        SELECT id, nome, descricao, preco, quantidade,
               categoria, status, data_cadastro
        FROM produtos ORDER BY id
        """,
        [
            ("ID", "id"),
            ("Nome", "nome"),
            ("Descrição", "descricao"),
            ("Preço", "preco"),
            ("Quantidade", "quantidade"),
            ("Categoria", "categoria"),
            ("Status", "status"),
            ("Data de cadastro", "data_cadastro"),
        ],
        acoes=("/produtos", "id")
    )


@app.route("/produtos/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_produto():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar produto", "/produtos/novo", CAMPOS_PRODUTO
        )

    dados, aviso = ler_produto()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        INSERT INTO produtos (
            nome, descricao, preco, quantidade,
            categoria, imagem, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        dados, "listar_produtos", "Não foi possível cadastrar o produto."
    )


@app.route("/produtos/<int:id_produto>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_produto(id_produto):
    registro = buscar_um(
        "SELECT * FROM produtos WHERE id = %s", (id_produto,)
    )
    if not registro:
        return erro_formulario("Produto não encontrado.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar produto", f"/produtos/{id_produto}/editar",
            CAMPOS_PRODUTO, registro
        )

    dados, aviso = ler_produto()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        UPDATE produtos
        SET nome = %s, descricao = %s, preco = %s, quantidade = %s,
            categoria = %s, imagem = %s, status = %s
        WHERE id = %s
        """,
        dados + (id_produto,), "listar_produtos",
        "Não foi possível atualizar o produto."
    )


@app.route("/produtos/<int:id_produto>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_produto(id_produto):
    return excluir("produtos", "id", id_produto, "listar_produtos")


# =====================================================
# MENSAGENS
# =====================================================

CAMPOS_MENSAGEM = [
    {"nome": "nome_remetente", "rotulo": "Nome do remetente",
     "obrigatorio": True, "maxlength": 150},
    {"nome": "email_remetente", "rotulo": "E-mail do remetente",
     "tipo": "email", "maxlength": 180},
    {"nome": "assunto", "rotulo": "Assunto",
     "obrigatorio": True, "maxlength": 200},
    {"nome": "mensagem", "rotulo": "Mensagem",
     "tipo": "textarea", "obrigatorio": True},
    {"nome": "resposta", "rotulo": "Resposta", "tipo": "textarea"},
    {"nome": "status", "rotulo": "Status", "tipo": "select",
     "obrigatorio": True,
     "opcoes": [
         ("não lida", "Não lida"),
         ("lida", "Lida"),
         ("respondida", "Respondida"),
     ]},
]

STATUS_MENSAGEM = ("não lida", "lida", "respondida")


def ler_mensagem():
    nome = texto("nome_remetente")
    assunto = texto("assunto")
    mensagem = texto("mensagem")
    status = texto("status") or "não lida"

    if not nome or not assunto or not mensagem:
        return None, "Preencha nome, assunto e mensagem."
    if status not in STATUS_MENSAGEM:
        return None, "Status inválido."

    return (
        nome,
        texto("email_remetente") or None,
        assunto,
        mensagem,
        texto("resposta") or None,
        status,
    ), None


@app.route("/mensagens")
def listar_mensagens():
    return listar_dados(
        "Mensagens recebidas",
        """
        SELECT id, nome_remetente, email_remetente, assunto,
               mensagem, resposta, status, data_envio
        FROM mensagens ORDER BY data_envio DESC
        """,
        [
            ("ID", "id"),
            ("Remetente", "nome_remetente"),
            ("E-mail", "email_remetente"),
            ("Assunto", "assunto"),
            ("Mensagem", "mensagem"),
            ("Resposta", "resposta"),
            ("Status", "status"),
            ("Data", "data_envio"),
        ],
        acoes=("/mensagens", "id")
    )


@app.route("/mensagens/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_mensagem():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar mensagem", "/mensagens/novo", CAMPOS_MENSAGEM
        )

    dados, aviso = ler_mensagem()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        INSERT INTO mensagens (
            nome_remetente, email_remetente, assunto,
            mensagem, resposta, status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        dados, "listar_mensagens",
        "Não foi possível cadastrar a mensagem."
    )


@app.route("/mensagens/<int:id_mensagem>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_mensagem(id_mensagem):
    registro = buscar_um(
        "SELECT * FROM mensagens WHERE id = %s", (id_mensagem,)
    )
    if not registro:
        return erro_formulario("Mensagem não encontrada.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar mensagem", f"/mensagens/{id_mensagem}/editar",
            CAMPOS_MENSAGEM, registro
        )

    dados, aviso = ler_mensagem()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        UPDATE mensagens
        SET nome_remetente = %s, email_remetente = %s, assunto = %s,
            mensagem = %s, resposta = %s, status = %s
        WHERE id = %s
        """,
        dados + (id_mensagem,), "listar_mensagens",
        "Não foi possível atualizar a mensagem."
    )


@app.route("/mensagens/<int:id_mensagem>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_mensagem(id_mensagem):
    return excluir("mensagens", "id", id_mensagem, "listar_mensagens")


# =====================================================
# CONFIGURACOES
# =====================================================

CAMPOS_CONFIGURACAO = [
    {"nome": "nome_site", "rotulo": "Nome do site",
     "obrigatorio": True, "maxlength": 150, "valor": "Meu Site"},
    {"nome": "email_contato", "rotulo": "E-mail de contato",
     "tipo": "email", "maxlength": 180},
    {"nome": "telefone", "rotulo": "Telefone", "maxlength": 30},
    {"nome": "endereco", "rotulo": "Endereço", "maxlength": 255},
    {"nome": "moeda", "rotulo": "Moeda",
     "obrigatorio": True, "maxlength": 10, "valor": "BRL"},
    {"nome": "notificacoes_ativas", "rotulo": "Notificações",
     "tipo": "select", "obrigatorio": True,
     "opcoes": [("1", "Ativadas"), ("0", "Desativadas")]},
]


def ler_configuracao():
    nome_site = texto("nome_site")
    moeda = texto("moeda")
    notificacoes = request.form.get("notificacoes_ativas", "1")

    if not nome_site or not moeda:
        return None, "Informe o nome do site e a moeda."
    if notificacoes not in ("0", "1"):
        return None, "Opção de notificação inválida."

    return (
        nome_site,
        texto("email_contato") or None,
        texto("telefone") or None,
        texto("endereco") or None,
        moeda,
        int(notificacoes),
    ), None


@app.route("/configuracoes")
def listar_configuracoes():
    return listar_dados(
        "Configurações do sistema",
        """
        SELECT id, nome_site, email_contato, telefone, endereco,
               moeda, notificacoes_ativas, data_atualizacao
        FROM configuracoes ORDER BY id
        """,
        [
            ("ID", "id"),
            ("Nome do site", "nome_site"),
            ("E-mail de contato", "email_contato"),
            ("Telefone", "telefone"),
            ("Endereço", "endereco"),
            ("Moeda", "moeda"),
            ("Notificações ativas (1 = sim)", "notificacoes_ativas"),
            ("Última atualização", "data_atualizacao"),
        ],
        acoes=("/configuracoes", "id")
    )


@app.route("/configuracoes/novo", methods=["GET", "POST"])
@tratar_erro_banco
def cadastrar_configuracao():
    if request.method == "GET":
        return formulario_html(
            "Cadastrar configuração", "/configuracoes/novo",
            CAMPOS_CONFIGURACAO
        )

    dados, aviso = ler_configuracao()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        INSERT INTO configuracoes (
            nome_site, email_contato, telefone, endereco,
            moeda, notificacoes_ativas
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        dados, "listar_configuracoes",
        "Não foi possível cadastrar a configuração."
    )


@app.route("/configuracoes/<int:id_config>/editar", methods=["GET", "POST"])
@tratar_erro_banco
def editar_configuracao(id_config):
    registro = buscar_um(
        "SELECT * FROM configuracoes WHERE id = %s", (id_config,)
    )
    if not registro:
        return erro_formulario("Configuração não encontrada.", 404)

    if request.method == "GET":
        return formulario_html(
            "Editar configuração", f"/configuracoes/{id_config}/editar",
            CAMPOS_CONFIGURACAO, registro
        )

    dados, aviso = ler_configuracao()
    if aviso:
        return erro_formulario(aviso)

    return salvar(
        """
        UPDATE configuracoes
        SET nome_site = %s, email_contato = %s, telefone = %s,
            endereco = %s, moeda = %s, notificacoes_ativas = %s
        WHERE id = %s
        """,
        dados + (id_config,), "listar_configuracoes",
        "Não foi possível atualizar a configuração."
    )


@app.route("/configuracoes/<int:id_config>/excluir", methods=["POST"])
@tratar_erro_banco
def excluir_configuracao(id_config):
    return excluir("configuracoes", "id", id_config, "listar_configuracoes")


# =====================================================
# EXECUCAO DO SISTEMA
# =====================================================

if __name__ == "__main__":
    # Em produção, use debug=False e um servidor WSGI (gunicorn/waitress).
    app.run(debug=False)


# ===== FIM DA PARTE 3 =====