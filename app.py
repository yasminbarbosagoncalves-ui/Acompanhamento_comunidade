from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from config import DB_CONFIG
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = 'chave_secreta_comunidade_girlpower'

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
    except mysql.connector.Error as erro:
        if conexao and conexao.is_connected():
            conexao.rollback()
        return str(erro) # Retorna o erro como texto para mostrarmos na tela
    finally:
        if cursor:
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()
    return None # Se não houve erro, retorna None

def consultar_sql(sql, parametros=()):
    conexao = None
    cursor = None
    try:
        conexao = conectar()
        # CORREÇÃO AQUI: Adicionado buffered=True
        cursor = conexao.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, parametros)
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()

def buscar_um(sql, parametros=()):
    conexao = None
    cursor = None
    try:
        conexao = conectar()
        # CORREÇÃO AQUI: Adicionado buffered=True
        cursor = conexao.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, parametros)
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()

# =====================================================
# PÁGINA INICIAL
# =====================================================

# =====================================================
# PÁGINA INICIAL
# =====================================================

@app.route("/")
def index():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    qtd_moradores = consultar_sql("SELECT COUNT(*) as total FROM morador")[0]['total']
    qtd_solicitacoes = consultar_sql("SELECT COUNT(*) as total FROM solicitacao")[0]['total']
    qtd_produtos = consultar_sql("SELECT COUNT(*) as total FROM produtos")[0]['total']
    qtd_mensagens = consultar_sql("SELECT COUNT(*) as total FROM mensagens")[0]['total']

    # NOVO: Buscar a contagem de solicitações por status
    status_counts = consultar_sql("""
        SELECT status, COUNT(*) as total 
        FROM solicitacao 
        GROUP BY status
    """)
    
    # Transformar em um dicionário para facilitar no HTML
    dados_grafico = {item['status']: item['total'] for item in status_counts}

    return render_template("index.html", 
                           moradores=qtd_moradores, 
                           solicitacoes=qtd_solicitacoes,
                           produtos=qtd_produtos,
                           mensagens=qtd_mensagens,
                           dados_grafico=dados_grafico) # <-- Passando para o HTML
          
# =====================================================
# AUTENTICAÇÃO (LOGIN E LOGOUT)
# =====================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_digitado = request.form.get("login", "").strip()
        senha_digitada = request.form.get("senha", "")

        if not login_digitado or not senha_digitada:
            return render_template("login.html", erro="Preencha login e senha.")

        # Busca o usuário no banco de dados
        usuario = buscar_um(
            "SELECT id_usuario, nome, login, senha, perfil FROM usuario WHERE login = %s",
            (login_digitado,)
        )

        # Verifica se o usuário existe e se a senha bate com o hash
        if not usuario or not check_password_hash(usuario["senha"], senha_digitada):
            return render_template("login.html", erro="Login ou senha inválidos.")

        # Salva os dados na sessão
        session["usuario_id"] = usuario["id_usuario"]
        session["usuario_nome"] = usuario["nome"]
        session["usuario_perfil"] = usuario["perfil"]

        return redirect(url_for("index"))

    # Se for GET, apenas mostra a tela de login
    return render_template("login.html", erro=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/perfil")
def perfil():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
        
    # Busca os dados atualizados do usuário logado
    usuario = buscar_um(
        "SELECT id_usuario, nome, login, perfil FROM usuario WHERE id_usuario = %s",
        (session["usuario_id"],)
    )
    
    if not usuario:
        return "Usuário não encontrado.", 404
        
    return render_template("perfil.html", usuario=usuario)

# =====================================================
# USUÁRIOS
# =====================================================

@app.route("/usuarios")
def listar_usuarios():
    busca = request.args.get("busca", "").strip()
    
    sql = "SELECT id_usuario, nome, login, perfil FROM usuario"
    parametros = ()
    
    if busca:
        sql += " WHERE nome LIKE %s OR login LIKE %s"
        parametros = (f"%{busca}%", f"%{busca}%")
        
    sql += " ORDER BY id_usuario"
    
    usuarios = consultar_sql(sql, parametros)
    return render_template("usuario.html", usuarios=usuarios, busca=busca)

@app.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):
    usuario = buscar_um("SELECT * FROM usuario WHERE id_usuario = %s", (id,))
    
    if not usuario:
        return "Usuário não encontrado.", 404

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        login = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")
        perfil = request.form.get("perfil", "").strip()
        
        # Se a senha foi preenchida, atualiza com o hash. Se ficou vazia, mantém a antiga.
        if senha:
            senha_hash = generate_password_hash(senha)
            erro = executar_sql(
                "UPDATE usuario SET nome=%s, login=%s, senha=%s, perfil=%s WHERE id_usuario=%s", 
                (nome, login, senha_hash, perfil, id)
            )
        else:
            erro = executar_sql(
                "UPDATE usuario SET nome=%s, login=%s, perfil=%s WHERE id_usuario=%s", 
                (nome, login, perfil, id)
            )
        
        if erro:
            flash(f'Erro ao atualizar: {erro}', 'danger')
        else:
            flash('Usuário atualizado com sucesso!', 'success')
            
        return redirect(url_for("listar_usuarios"))
        
    return render_template("usuario_form.html", usuario=usuario)

@app.route("/usuarios/novo", methods=["GET", "POST"])
def cadastrar_usuario():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        login = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")
        perfil = request.form.get("perfil", "").strip()
        
        if not nome or not login or not senha or not perfil:
            return "Preencha todos os campos obrigatórios.", 400
            
        senha_hash = generate_password_hash(senha)
        erro = executar_sql(
            "INSERT INTO usuario (nome, login, senha, perfil) VALUES (%s, %s, %s, %s)",
            (nome, login, senha_hash, perfil)
        )
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Usuário cadastrado com sucesso!', 'success')
        return redirect(url_for("listar_usuarios"))
        
    return render_template("usuario_form.html")

# =====================================================
# MORADORES
# =====================================================

@app.route("/moradores")
def listar_moradores():
    busca = request.args.get("busca", "").strip()

    sql = """
        SELECT m.*, u.nome as nome_usuario 
        FROM morador m 
        JOIN usuario u ON m.id_usuario = u.id_usuario
    """
    parametros = ()
    
    if busca:
        sql += " WHERE m.nome LIKE %s OR m.cpf LIKE %s"
        parametros = (f"%{busca}%", f"%{busca}%")
        
    sql += " ORDER BY m.id_morador"
    
    moradores = consultar_sql(sql, parametros)
    return render_template("morador.html", moradores=moradores, busca=busca)

@app.route("/moradores/novo", methods=["GET", "POST"])
def cadastrar_morador():
    usuarios = consultar_sql("SELECT id_usuario, nome FROM usuario ORDER BY nome")
    
    if request.method == "POST":
        id_usuario = request.form.get("id_usuario")
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        telefone = request.form.get("telefone", "").strip()
        email = request.form.get("email", "").strip()
        endereco = request.form.get("endereco", "").strip()
        
        if not id_usuario or not nome or not cpf:
            return "Preencha os campos obrigatórios (Usuário, Nome e CPF).", 400
            
        erro = executar_sql(
            "INSERT INTO morador (id_usuario, nome, cpf, telefone, email, endereco) VALUES (%s, %s, %s, %s, %s, %s)",
            (id_usuario, nome, cpf, telefone or None, email or None, endereco or None)
        )
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Morador cadastrado com sucesso!', 'success')
        return redirect(url_for("listar_moradores"))
        
    return render_template("morador_form.html", usuarios=usuarios)

@app.route("/moradores/editar/<int:id>", methods=["GET", "POST"])
def editar_morador(id):
    morador = buscar_um("SELECT * FROM morador WHERE id_morador = %s", (id,))
    usuarios = consultar_sql("SELECT id_usuario, nome FROM usuario ORDER BY nome")
    
    if not morador:
        return "Morador não encontrado.", 404

    if request.method == "POST":
        id_usuario = request.form.get("id_usuario")
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        telefone = request.form.get("telefone", "").strip()
        email = request.form.get("email", "").strip()
        endereco = request.form.get("endereco", "").strip()
        
        if not id_usuario or not nome or not cpf:
            flash('Preencha os campos obrigatórios.', 'danger')
            return redirect(url_for("editar_morador", id=id))
            
        erro = executar_sql("""
            UPDATE morador 
            SET id_usuario = %s, nome = %s, cpf = %s, telefone = %s, email = %s, endereco = %s
            WHERE id_morador = %s
        """, (id_usuario, nome, cpf, telefone or None, email or None, endereco or None, id))
        
        if erro:
            flash(f'Erro ao atualizar: {erro}', 'danger')
            return redirect(url_for("editar_morador", id=id))
            
        flash('Morador atualizado com sucesso!', 'success')
        return redirect(url_for("listar_moradores"))
        
    return render_template("morador_form.html", usuarios=usuarios, morador=morador)

@app.route("/moradores/excluir/<int:id>")
def excluir_morador(id):
    # Busca o ID do usuário vinculado antes de apagar
    morador = buscar_um("SELECT id_usuario FROM morador WHERE id_morador = %s", (id,))
    
    if morador:
        # Apaga o morador
        executar_sql("DELETE FROM morador WHERE id_morador = %s", (id,))
        # Apaga o usuário vinculado (opcional, mas recomendado)
        executar_sql("DELETE FROM usuario WHERE id_usuario = %s", (morador['id_usuario'],))
        
        flash('Morador excluído com sucesso!', 'success')
        
    return redirect(url_for("listar_moradores"))

# =====================================================
# SETORES
# =====================================================

@app.route("/setores")
def listar_setores():
    setores = consultar_sql("SELECT * FROM setor ORDER BY id_setor")
    return render_template("setor.html", setores=setores)

@app.route("/setores/novo", methods=["GET", "POST"])
def cadastrar_setor():
    if request.method == "POST":
        nome = request.form.get("nome_setor", "").strip()
        responsavel = request.form.get("responsavel", "").strip()
        
        if not nome:
            return "Informe o nome do setor.", 400
            
        erro = executar_sql(
            "INSERT INTO setor (nome_setor, responsavel) VALUES (%s, %s)",
            (nome, responsavel or None)
        )
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Setor cadastrado com sucesso!', 'success')
        return redirect(url_for("listar_setores"))
        
    return render_template("setor_form.html")

# =====================================================
# CATEGORIAS
# =====================================================

@app.route("/categorias")
def listar_categorias():
    categorias = consultar_sql("SELECT * FROM categoria ORDER BY id_categoria")
    return render_template("categoria.html", categorias=categorias)

@app.route("/categorias/novo", methods=["GET", "POST"])
def cadastrar_categoria():
    if request.method == "POST":
        nome = request.form.get("nome_categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        
        if not nome:
            return "Informe o nome da categoria.", 400
            
        erro = executar_sql(
            "INSERT INTO categoria (nome_categoria, descricao) VALUES (%s, %s)",
            (nome, descricao or None)
        )
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Categoria cadastrada com sucesso!', 'success')
        return redirect(url_for("listar_categorias"))
        
    return render_template("categoria_form.html")

# =====================================================
# FUNCIONÁRIOS
# =====================================================

@app.route("/funcionarios")
def listar_funcionarios():
    funcionarios = consultar_sql("""
        SELECT f.*, u.nome as nome_usuario, s.nome_setor 
        FROM funcionario f
        JOIN usuario u ON f.id_usuario = u.id_usuario
        JOIN setor s ON f.id_setor = s.id_setor
        ORDER BY f.id_funcionario
    """)
    return render_template("funcionario.html", funcionarios=funcionarios)

@app.route("/funcionarios/novo", methods=["GET", "POST"])
def cadastrar_funcionario():
    usuarios = consultar_sql("SELECT id_usuario, nome FROM usuario ORDER BY nome")
    setores = consultar_sql("SELECT id_setor, nome_setor FROM setor ORDER BY nome_setor")
    
    if request.method == "POST":
        id_usuario = request.form.get("id_usuario")
        id_setor = request.form.get("id_setor")
        nome = request.form.get("nome", "").strip()
        matricula = request.form.get("matricula", "").strip()
        cargo = request.form.get("cargo", "").strip()
        
        if not id_usuario or not id_setor or not nome or not matricula:
            return "Preencha todos os campos obrigatórios.", 400
            
        erro = executar_sql(
            "INSERT INTO funcionario (id_usuario, id_setor, nome, matricula, cargo) VALUES (%s, %s, %s, %s, %s)",
            (id_usuario, id_setor, nome, matricula, cargo or None)
        )
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Funcionário cadastrado com sucesso!', 'success')
        return redirect(url_for("listar_funcionarios"))
        
    return render_template("funcionario_form.html", usuarios=usuarios, setores=setores)

# =====================================================
# SOLICITAÇÕES
# =====================================================

@app.route("/solicitacoes")
def listar_solicitacoes():
    busca = request.args.get("busca", "").strip()

    sql = """
        SELECT so.*, m.nome AS morador, c.nome_categoria AS categoria, se.nome_setor AS setor
        FROM solicitacao so
        JOIN morador m ON so.id_morador = m.id_morador
        JOIN categoria c ON so.id_categoria = c.id_categoria
        JOIN setor se ON so.id_setor = se.id_setor
    """
    parametros = ()
    
    if busca:
        sql += " WHERE so.protocolo LIKE %s OR m.nome LIKE %s"
        parametros = (f"%{busca}%", f"%{busca}%")
        
    sql += " ORDER BY so.id_solicitacao DESC" # Mais recentes primeiro
    
    solicitacoes = consultar_sql(sql, parametros)
    return render_template("solicitacao.html", solicitacoes=solicitacoes, busca=busca)

@app.route("/solicitacoes/editar/<int:id>", methods=["GET", "POST"])
def editar_solicitacao(id):
    # Busca a solicitação e as listas para os selects
    solicitacao = buscar_um("SELECT * FROM solicitacao WHERE id_solicitacao = %s", (id,))
    moradores = consultar_sql("SELECT id_morador, nome FROM morador ORDER BY nome")
    categorias = consultar_sql("SELECT id_categoria, nome_categoria FROM categoria ORDER BY nome_categoria")
    setores = consultar_sql("SELECT id_setor, nome_setor FROM setor ORDER BY nome_setor")
    
    if not solicitacao:
        return "Solicitação não encontrada.", 404

    if request.method == "POST":
        id_morador = request.form.get("id_morador")
        id_categoria = request.form.get("id_categoria")
        id_setor = request.form.get("id_setor")
        protocolo = request.form.get("protocolo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        localizacao = request.form.get("localizacao", "").strip()
        data_registro = request.form.get("data_registro")
        status = request.form.get("status", "").strip()
        
        erro = executar_sql("""
            UPDATE solicitacao 
            SET id_morador=%s, id_categoria=%s, id_setor=%s, protocolo=%s, descricao=%s, localizacao=%s, data_registro=%s, status=%s
            WHERE id_solicitacao=%s
        """, (id_morador, id_categoria, id_setor, protocolo, descricao, localizacao, data_registro, status, id))
        
        if erro:
            flash(f'Erro ao atualizar: {erro}', 'danger')
            return redirect(url_for("editar_solicitacao", id=id))
            
        flash('Solicitação atualizada com sucesso!', 'success')
        return redirect(url_for("listar_solicitacoes"))
        
    return render_template("solicitacao_form.html", 
                           solicitacao=solicitacao, 
                           moradores=moradores, 
                           categorias=categorias, 
                           setores=setores)

@app.route("/solicitacoes/excluir/<int:id>")
def excluir_solicitacao(id):
    # Primeiro apaga o histórico atrelado (para não dar erro de Foreign Key)
    executar_sql("DELETE FROM historico WHERE id_solicitacao = %s", (id,))
    # Depois apaga a solicitação
    executar_sql("DELETE FROM solicitacao WHERE id_solicitacao = %s", (id,))
    
    flash('Solicitação e seu histórico foram excluídos!', 'success')
    return redirect(url_for("listar_solicitacoes"))

@app.route("/solicitacoes/novo", methods=["GET", "POST"])
def cadastrar_solicitacao():
    moradores = consultar_sql("SELECT id_morador, nome FROM morador ORDER BY nome")
    categorias = consultar_sql("SELECT id_categoria, nome_categoria FROM categoria ORDER BY nome_categoria")
    setores = consultar_sql("SELECT id_setor, nome_setor FROM setor ORDER BY nome_setor")
    
    if request.method == "POST":
        id_morador = request.form.get("id_morador")
        id_categoria = request.form.get("id_categoria")
        id_setor = request.form.get("id_setor")
        protocolo = request.form.get("protocolo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        localizacao = request.form.get("localizacao", "").strip()
        data_registro = request.form.get("data_registro")
        status = request.form.get("status", "").strip()
        
        if not all([id_morador, id_categoria, id_setor, protocolo, descricao, localizacao, data_registro, status]):
            return "Preencha todos os campos obrigatórios.", 400
            
        erro = executar_sql("""
            INSERT INTO solicitacao (id_morador, id_categoria, id_setor, protocolo, descricao, localizacao, data_registro, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (id_morador, id_categoria, id_setor, protocolo, descricao, localizacao, data_registro, status))
        
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Solicitação registrada com sucesso!', 'success')
        return redirect(url_for("listar_solicitacoes"))
        
    return render_template("solicitacao_form.html", moradores=moradores, categorias=categorias, setores=setores)

@app.route("/solicitacoes/<int:id>")
def detalhes_solicitacao(id):
    # Busca os dados da solicitação específica com os JOINs
    solicitacao = buscar_um("""
        SELECT so.*, m.nome AS morador, m.cpf, m.telefone, m.email, 
               c.nome_categoria AS categoria, se.nome_setor AS setor
        FROM solicitacao so
        JOIN morador m ON so.id_morador = m.id_morador
        JOIN categoria c ON so.id_categoria = c.id_categoria
        JOIN setor se ON so.id_setor = se.id_setor
        WHERE so.id_solicitacao = %s
    """, (id,))
    
    if not solicitacao:
        return "Solicitação não encontrada.", 404
        
    # Busca o histórico dessa solicitação
    historico = consultar_sql("""
        SELECT h.*, f.nome AS funcionario
        FROM historico h
        JOIN funcionario f ON h.id_funcionario = f.id_funcionario
        WHERE h.id_solicitacao = %s
        ORDER BY h.data_alteracao ASC
    """, (id,))
    
    return render_template("solicitacao_detalhes.html", solicitacao=solicitacao, historico=historico)

# =====================================================
# HISTÓRICO
# =====================================================

@app.route("/historico")
def listar_historico():
    historicos = consultar_sql("""
        SELECT h.*, so.protocolo, f.nome AS funcionario
        FROM historico h
        JOIN solicitacao so ON h.id_solicitacao = so.id_solicitacao
        JOIN funcionario f ON h.id_funcionario = f.id_funcionario
        ORDER BY h.id_historico
    """)
    return render_template("historico.html", historicos=historicos)

@app.route("/historico/novo", methods=["GET", "POST"])
def cadastrar_historico():
    solicitacoes = consultar_sql("SELECT id_solicitacao, protocolo FROM solicitacao ORDER BY id_solicitacao")
    funcionarios = consultar_sql("SELECT id_funcionario, nome FROM funcionario ORDER BY nome")
    
    if request.method == "POST":
        id_solicitacao = request.form.get("id_solicitacao")
        id_funcionario = request.form.get("id_funcionario")
        status_anterior = request.form.get("status_anterior", "").strip()
        novo_status = request.form.get("novo_status", "").strip()
        data_alteracao = request.form.get("data_alteracao")
        observacao = request.form.get("observacao", "").strip()
        
        if not id_solicitacao or not id_funcionario or not status_anterior or not novo_status or not data_alteracao:
            return "Preencha todos os campos obrigatórios.", 400
            
        erro = executar_sql("""
            INSERT INTO historico (id_solicitacao, id_funcionario, status_anterior, novo_status, data_alteracao, observacao)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id_solicitacao, id_funcionario, status_anterior, novo_status, data_alteracao, observacao or None))
        
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Histórico registrado com sucesso!', 'success')
        return redirect(url_for("listar_historico"))
        
    return render_template("historico_form.html", solicitacoes=solicitacoes, funcionarios=funcionarios)

# =====================================================
# PRODUTOS
# =====================================================

@app.route("/produtos")
def listar_produtos():
    busca = request.args.get("busca", "").strip()
    sql = "SELECT * FROM produtos"
    parametros = ()
    
    if busca:
        sql += " WHERE nome LIKE %s OR categoria LIKE %s"
        parametros = (f"%{busca}%", f"%{busca}%")
        
    sql += " ORDER BY id DESC"
    produtos = consultar_sql(sql, parametros)
    return render_template("produtos.html", produtos=produtos, busca=busca)

@app.route("/produtos/editar/<int:id>", methods=["GET", "POST"])
def editar_produto(id):
    produto = buscar_um("SELECT * FROM produtos WHERE id = %s", (id,))
    if not produto:
        return "Produto não encontrado.", 404

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        preco = request.form.get("preco", "0.00")
        quantidade = request.form.get("quantidade", "0")
        categoria = request.form.get("categoria", "").strip()
        imagem = request.form.get("imagem", "").strip()
        status = request.form.get("status", "ativo")
        
        try:
            preco_dec = Decimal(preco)
            qtd_int = int(quantidade)
        except (InvalidOperation, ValueError):
            flash('Preço ou quantidade inválidos.', 'danger')
            return redirect(url_for("editar_produto", id=id))
            
        erro = executar_sql("""
            UPDATE produtos SET nome=%s, descricao=%s, preco=%s, quantidade=%s, categoria=%s, imagem=%s, status=%s
            WHERE id=%s
        """, (nome, descricao or None, preco_dec, qtd_int, categoria or None, imagem or None, status, id))
        
        if erro:
            flash(f'Erro ao atualizar: {erro}', 'danger')
        else:
            flash('Produto atualizado com sucesso!', 'success')
            
        return redirect(url_for("listar_produtos"))
        
    return render_template("produtos_form.html", produto=produto)

@app.route("/produtos/excluir/<int:id>")
def excluir_produto(id):
    executar_sql("DELETE FROM produtos WHERE id = %s", (id,))
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for("listar_produtos"))

@app.route("/produtos/novo", methods=["GET", "POST"])
def cadastrar_produto():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        preco = request.form.get("preco", "0.00")
        quantidade = request.form.get("quantidade", "0")
        categoria = request.form.get("categoria", "").strip()
        imagem = request.form.get("imagem", "").strip()
        status = request.form.get("status", "ativo")
        
        if not nome:
            return "Informe o nome do produto.", 400
            
        try:
            preco_dec = Decimal(preco)
            qtd_int = int(quantidade)
        except (InvalidOperation, ValueError):
            return "Preço ou quantidade inválidos.", 400
            
        erro = executar_sql("""
            INSERT INTO produtos (nome, descricao, preco, quantidade, categoria, imagem, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nome, descricao or None, preco_dec, qtd_int, categoria or None, imagem or None, status))
        
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for("listar_produtos"))
        
    return render_template("produtos_form.html")

# =====================================================
# MENSAGENS
# =====================================================

@app.route("/mensagens")
def listar_mensagens():
    mensagens = consultar_sql("SELECT * FROM mensagens ORDER BY data_envio DESC")
    return render_template("mensagens.html", mensagens=mensagens)

@app.route("/mensagens/novo", methods=["GET", "POST"])
def cadastrar_mensagem():
    if request.method == "POST":
        nome_remetente = request.form.get("nome_remetente", "").strip()
        email_remetente = request.form.get("email_remetente", "").strip()
        assunto = request.form.get("assunto", "").strip()
        mensagem = request.form.get("mensagem", "").strip()
        resposta = request.form.get("resposta", "").strip()
        status = request.form.get("status", "não lida")
        
        if not nome_remetente or not assunto or not mensagem:
            return "Preencha os campos obrigatórios (Remetente, Assunto e Mensagem).", 400
            
        erro = executar_sql("""
            INSERT INTO mensagens (nome_remetente, email_remetente, assunto, mensagem, resposta, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nome_remetente, email_remetente or None, assunto, mensagem, resposta or None, status))
        
        if erro:
            return f"Erro ao cadastrar: {erro}"
            
        flash('Mensagem enviada com sucesso!', 'success')
        return redirect(url_for("listar_mensagens"))
        
    return render_template("mensagens_form.html")


# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == "__main__":
    app.run(debug=True)