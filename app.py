from flask import Flask
import mysql.connector
from config import DB_CONFIG
from html import escape

app = Flask(__name__)


# Conexão com o banco de dados
def conectar():
    return mysql.connector.connect(**DB_CONFIG)


# Função reutilizável para consultar e exibir tabelas
def listar_dados(titulo, sql, colunas):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql)
        registros = cursor.fetchall()

        html = f"""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{escape(titulo)}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 30px;
                    background: #f4f6f9;
                    color: #222;
                }}
                h1 {{ color: #245b45; }}
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
                tr:nth-child(even) {{ background: #eef3f0; }}
                a {{ color: #176b4d; }}
                .voltar {{ display: inline-block; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>{escape(titulo)}</h1>
            <a class="voltar" href="/">← Voltar ao início</a>
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

        html += "</body></html>"
        return html

    except mysql.connector.Error as erro:
        return f"<h1>Erro no banco de dados</h1><p>{escape(str(erro))}</p>", 500

    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None and conexao.is_connected():
            conexao.close()


# Página inicial
@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Acompanhamento da Comunidade</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f9;
                margin: 40px;
            }
            h1 { color: #245b45; }
            ul { line-height: 2.2; }
            a { color: #176b4d; }
        </style>
    </head>
    <body>
        <h1>Sistema de Acompanhamento da Comunidade</h1>
        <p>Bem-vindo ao sistema de gestão comunitária.</p>

        <h2>Consultas do sistema</h2>
        <ul>
            <li><a href="/usuarios">Usuários</a></li>
            <li><a href="/moradores">Moradores</a></li>
            <li><a href="/setores">Setores</a></li>
            <li><a href="/funcionarios">Funcionários</a></li>
            <li><a href="/categorias">Categorias</a></li>
            <li><a href="/solicitacoes">Solicitações</a></li>
            <li><a href="/historico">Histórico</a></li>
            <li><a href="/produtos">Produtos</a></li>
            <li><a href="/mensagens">Mensagens</a></li>
            <li><a href="/configuracoes">Configurações</a></li>
        </ul>
    </body>
    </html>
    """


# 1. Usuários
@app.route("/usuarios")
def listar_usuarios():
    return listar_dados(
        "Usuários cadastrados",
        """
        SELECT id_usuario, nome, login, perfil
        FROM usuario
        ORDER BY id_usuario
        """,
        [
            ("ID", "id_usuario"),
            ("Nome", "nome"),
            ("Login", "login"),
            ("Perfil", "perfil")
        ]
    )


# 2. Moradores
@app.route("/moradores")
def listar_moradores():
    return listar_dados(
        "Moradores cadastrados",
        """
        SELECT id_morador, nome, cpf, telefone, email, endereco
        FROM morador
        ORDER BY id_morador
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


# 3. Setores
@app.route("/setores")
def listar_setores():
    return listar_dados(
        "Setores",
        """
        SELECT id_setor, nome_setor, responsavel
        FROM setor
        ORDER BY id_setor
        """,
        [
            ("ID", "id_setor"),
            ("Nome do setor", "nome_setor"),
            ("Responsável", "responsavel")
        ]
    )


# 4. Funcionários
@app.route("/funcionarios")
def listar_funcionarios():
    return listar_dados(
        "Funcionários",
        """
        SELECT
            f.id_funcionario,
            f.nome,
            f.matricula,
            f.cargo,
            s.nome_setor AS setor
        FROM funcionario f
        INNER JOIN setor s
            ON f.id_setor = s.id_setor
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


# 5. Categorias
@app.route("/categorias")
def listar_categorias():
    return listar_dados(
        "Categorias de solicitações",
        """
        SELECT id_categoria, nome_categoria, descricao
        FROM categoria
        ORDER BY id_categoria
        """,
        [
            ("ID", "id_categoria"),
            ("Categoria", "nome_categoria"),
            ("Descrição", "descricao")
        ]
    )


# 6. Solicitações
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


# 7. Histórico das solicitações
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


# 8. Produtos
@app.route("/produtos")
def listar_produtos():
    return listar_dados(
        "Produtos cadastrados",
        """
        SELECT
            id, nome, descricao, preco, quantidade,
            categoria, status, data_cadastro
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


# 9. Mensagens
@app.route("/mensagens")
def listar_mensagens():
    return listar_dados(
        "Mensagens recebidas",
        """
        SELECT
            id, nome_remetente, email_remetente,
            assunto, mensagem, resposta, status, data_envio
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


# 10. Configurações
@app.route("/configuracoes")
def listar_configuracoes():
   return listar_dados(
        "Configurações do sistema",
        """
        SELECT
            id, nome_site, email_contato, telefone,
            endereco, moeda, notificacoes_ativas,
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


if __name__ == "__main__":
    app.run(debug=True)