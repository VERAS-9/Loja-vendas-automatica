import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
from functools import wraps
import secrets
from datetime import datetime
from dotenv import load_dotenv
import database
app = Flask(__name__)
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect('/') 
        return f(*args, **kwargs)
    return decorated_function
database.inicializar_banco()


load_dotenv()

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'chave_padrao_caso_falhe')
app.config['TEMPLATES_AUTO_RELOAD'] = True

WEBHOOK_VENDAS_CONCLUIDAS = os.environ.get("WEBHOOK_VENDAS")
WEBHOOK_NOVOS_PEDIDOS = os.environ.get("WEBHOOK_PEDIDOS")



oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),      
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'), 
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
    redirect_uri='https://sniperarena-store.discloud.app/auth/google/callback'
)
discord = oauth.register(
    name='discord',
    client_id=os.environ.get('DISCORD_CLIENT_ID'),
    client_secret=os.environ.get('DISCORD_CLIENT_SECRET'),
    access_token_url='https://discord.com/api/oauth2/token',
    authorize_url='https://discord.com/api/oauth2/authorize',
    api_base_url='https://discord.com/api/',
    client_kwargs={'scope': 'identify email'}
)

def get_db_connection():
    conn = sqlite3.connect('banco.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            verificado INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user',
            foto TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nick_roblox TEXT,
            produto TEXT,
            preco TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recuperacao_senha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT UNIQUE NOT NULL,
            expiracao TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            user_id INTEGER,
            remetente TEXT,
            mensagem TEXT,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN foto TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

PRODUTOS_FIXOS = [
    {"id": 1, "nome": "1K Cash", "preco": "R$ 3,50", "descricao": "Adicione 1K de cash à sua conta."},
    {"id": 2, "nome": "5K Cash", "preco": "R$ 17,50", "descricao": "Adicione 5K de cash à sua conta."},
    {"id": 3, "nome": "10K Cash", "preco": "R$ 35,00", "descricao": "Adicione 10K de cash à sua conta."},
    {"id": 4, "nome": "20K Cash", "preco": "R$ 70,00", "descricao": "Adicione 20K de cash à sua conta."},
    {"id": 5, "nome": "30K Cash", "preco": "R$ 105,00", "descricao": "Adicione 30K de cash à sua conta."},
    {"id": 6, "nome": "40K Cash", "preco": "R$ 140,00", "descricao": "Adicione 40K de cash à sua conta."},
    {"id": 7, "nome": "50K Cash", "preco": "R$ 175,00", "descricao": "Adicione 50K de cash à sua conta."},
    {"id": 8, "nome": "Passe de Batalha", "preco": "R$ 25,00", "descricao": "Desbloqueie o Passe no jogo."},
    {"id": 9, "nome": "5 Caixas", "preco": "R$ 10,00", "descricao": "Combo com 5 caixas secretas."}
]


@app.route("/")
def home():
    usuario_logado = session.get('username')
    return render_template("home.html", usuario_logado=usuario_logado)

@app.route("/pacotes")
def pacotes():
    usuario_logado = session.get('username')
    return render_template("index.html", produtos=PRODUTOS_FIXOS, usuario_logado=usuario_logado)

@app.route("/kits")
def kits():
    usuario_logado = session.get('username')
    return render_template("kits.html", usuario_logado=usuario_logado)

@app.route("/termos")
def termos():
    usuario_logado = session.get('username')
    return render_template("termos.html", usuario_logado=usuario_logado)

@app.route("/privacidade")
def privacidade():
    usuario_logado = session.get('username')
    return render_template("privacidade.html", usuario_logado=usuario_logado)

@app.route("/quantidade", methods=["GET", "POST"])
def quantidade():
    tabela_precos = {
        "cash": {"nome": "Cash (Unidade)", "valor_unitario": 0.0035},
        "passe": {"nome": "Passe de Batalha", "valor_unitario": 25.00},
        "caixa": {"nome": "Caixa Secreta", "valor_unitario": 2.00}
    }
    
    
    total = None
    item_escolhido = None
    qtd = 1

    if request.method == "POST":
        tipo = request.form.get("tipo")
        try:
            qtd = int(request.form.get("quantidade", 1))
        except ValueError:
            qtd = 1
            
        if tipo in tabela_precos:
            item_info = tabela_precos[tipo]
            item_escolhido = item_info["nome"]
            calculo = float(qtd) * float(item_info["valor_unitario"])
            total = f"{calculo:.2f}".replace('.', ',')

    usuario_logado = session.get('username')
    return render_template("quantidade.html", total=total, item=item_escolhido, qtd=qtd, usuario_logado=usuario_logado)
# --- ROTA PARA O ADMIN VER A LISTA DE CHATS ---
@app.route('/admin/chats')
@admin_required
def admin_chats():
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT p.id, p.produto, p.nick_roblox, p.status, u.username 
        FROM pedidos p
        JOIN usuarios u ON p.user_id = u.id
        JOIN chat_pedidos c ON p.id = c.pedido_id
        ORDER BY p.id DESC
    """
    cursor.execute(query)
    chats = cursor.fetchall()
    conn.close()

    return render_template('admin_chats.html', chats=chats)


# --- ROTA PARA O ADMIN RESPONDER UM CHAT ESPECÍFICO ---
@app.route('/admin/chat/<int:pedido_id>', methods=['GET', 'POST'])
@admin_required
def admin_chat_individual(pedido_id):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        mensagem = request.form.get('mensagem')
        if mensagem:
            cursor.execute("""
                INSERT INTO chat_pedidos (pedido_id, user_id, remetente, mensagem) 
                VALUES (?, ?, 'admin', ?)
            """, (pedido_id, session['user_id'], mensagem))
            conn.commit()
            return redirect(url_for('admin_chat_individual', pedido_id=pedido_id))

    cursor.execute("SELECT produto, nick_roblox, status FROM pedidos WHERE id = ?", (pedido_id,))
    pedido = cursor.fetchone()

    cursor.execute("""
        SELECT remetente, mensagem, data_envio 
        FROM chat_pedidos 
        WHERE pedido_id = ? 
        ORDER BY data_envio ASC
    """, (pedido_id,))
    mensagens = cursor.fetchall()
    
    conn.close()

    return render_template('admin_chat_individual.html', pedido=pedido, mensagens=mensagens, pedido_id=pedido_id)

@app.route("/perfil")
def perfil():
    if not session.get('user_id'):
        return redirect(url_for('pacotes'))

    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    usuario = cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    meus_pedidos = cursor.execute("SELECT * FROM pedidos WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    
    conn.close()

    return render_template("perfil.html", usuario=usuario, pedidos=meus_pedidos, usuario_logado=session.get('username'))

@app.route("/pedido/<int:pedido_id>")
def detalhe_pedido(pedido_id):
    if not session.get('user_id'):
        return redirect(url_for('pacotes'))

    user_id = session.get('user_id')
    user_role = session.get('role', 'user')

    conn = get_db_connection()
    cursor = conn.cursor()

    if user_role == 'admin':
        pedido = cursor.execute("""
            SELECT p.*, u.username as cliente_nome, u.foto as cliente_foto 
            FROM pedidos p 
            LEFT JOIN usuarios u ON p.user_id = u.id 
            WHERE p.id = ?
        """, (pedido_id,)).fetchone()
    else:
        pedido = cursor.execute("""
            SELECT p.*, u.username as cliente_nome, u.foto as cliente_foto 
            FROM pedidos p 
            LEFT JOIN usuarios u ON p.user_id = u.id 
            WHERE p.id = ? AND p.user_id = ?
        """, (pedido_id, user_id)).fetchone()

    if not pedido:
        conn.close()
        return redirect(url_for('perfil'))

    mensagens = cursor.execute("""
        SELECT c.*, u.username, u.foto 
        FROM chat_pedidos c 
        LEFT JOIN usuarios u ON c.user_id = u.id 
        WHERE c.pedido_id = ? 
        ORDER BY c.id ASC
    """, (pedido_id,)).fetchall()

    conn.close()

    return render_template("pedido_detalhe.html", 
                           pedido=pedido, 
                           mensagens=mensagens, 
                           usuario_logado=session.get('username'))

@app.route("/pedido/<int:pedido_id>/enviar_mensagem", methods=["POST"])
def enviar_mensagem_chat(pedido_id):
    if not session.get('user_id'):
        return jsonify({"sucesso": False, "mensagem": "Não autorizado"}), 403

    user_id = session.get('user_id')
    user_role = session.get('role', 'user')
    dados = request.json
    mensagem = dados.get('mensagem', '').strip()

    if not mensagem:
        return jsonify({"sucesso": False, "mensagem": "Mensagem vazia"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    pedido = cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if not pedido:
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Pedido não encontrado"}), 404

    if user_role != 'admin' and pedido['user_id'] != user_id:
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Acesso negado"}), 403

    remetente = "Admin" if user_role == 'admin' else "Cliente"

    cursor.execute("""
        INSERT INTO chat_pedidos (pedido_id, user_id, remetente, mensagem) 
        VALUES (?, ?, ?, ?)
    """, (pedido_id, user_id, remetente, mensagem))
    conn.commit()
    conn.close()

    return jsonify({"sucesso": True})


@app.route("/admin")
@admin_required
def painel_admin():
    filtro_status = request.args.get('status', 'todos')

    conn = get_db_connection()
    cursor = conn.cursor()

    if filtro_status in ['Pendente', 'Aprovado', 'Recusado']:
        pedidos = cursor.execute("""
            SELECT p.id, u.username, p.nick_roblox, p.produto, p.preco, p.status 
            FROM pedidos p 
            LEFT JOIN usuarios u ON p.user_id = u.id 
            WHERE p.status = ?
            ORDER BY p.id DESC
        """, (filtro_status,)).fetchall()
    else:
        pedidos = cursor.execute("""
            SELECT p.id, u.username, p.nick_roblox, p.produto, p.preco, p.status 
            FROM pedidos p 
            LEFT JOIN usuarios u ON p.user_id = u.id 
            ORDER BY p.id DESC
        """).fetchall()

    todos_precos = cursor.execute("SELECT preco FROM pedidos").fetchall()
    valor_total = 0.0
    for p in todos_precos:
        if p['preco']:
            limpo = p['preco'].replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            try:
                valor_total += float(limpo)
            except ValueError:
                pass

    resumo_produtos = cursor.execute("""
        SELECT produto, COUNT(*) as quantidade_vendida 
        FROM pedidos 
        GROUP BY produto
    """).fetchall()

    conn.close()

    valor_total_str = f"{valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    return render_template("admin.html", 
                           pedidos=pedidos, 
                           valor_total=valor_total_str, 
                           resumo_produtos=resumo_produtos,
                           usuario_logado=session.get('username'),
                           filtro_atual=filtro_status)

@app.route("/admin/aprovar/<int:pedido_id>", methods=["POST"])
@admin_required
def aprovar_pedido(pedido_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    pedido = cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    
    if not pedido:
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Pedido não encontrado"}), 404

    cursor.execute("UPDATE pedidos SET status = 'Aprovado' WHERE id = ?", (pedido_id,))
    conn.commit()
    conn.close()

    try:
        payload = {
            "username": "Sniper Arena - Bot de Vendas",
            "embeds": [
                {
                    "title": f"✅ Pedido #{pedido_id} Aprovado com Sucesso!",
                    "color": 22433,
                    "fields": [
                        {"name": "📦 Produto", "value": f"```{pedido['produto']}```", "inline": True},
                        {"name": "💰 Valor", "value": f"```{pedido['preco']}```", "inline": True},
                        {"name": "👤 Nick do Cliente", "value": f"```{pedido['nick_roblox']}```", "inline": False}
                    ],
                    "footer": {"text": "Sniper Arena Store — Gestão de Vendas"}
                }
            ]
        }
        if WEBHOOK_VENDAS_CONCLUIDAS:
            requests.post(WEBHOOK_VENDAS_CONCLUIDAS, json=payload)
    except Exception as e:
        print(f"Erro ao enviar webhook de aprovação: {e}")

    return jsonify({"sucesso": True})

@app.route("/admin/recusar/<int:pedido_id>", methods=["POST"])
@admin_required
def recusar_pedido(pedido_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    pedido = cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    
    if not pedido:
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Pedido não encontrado"}), 404

    cursor.execute("UPDATE pedidos SET status = 'Recusado' WHERE id = ?", (pedido_id,))
    conn.commit()
    conn.close()

    return jsonify({"sucesso": True})

@app.route("/admin/resetar", methods=["POST"])
@admin_required
def resetar_pedidos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pedidos")
    conn.commit()
    conn.close()

    return jsonify({"sucesso": True})

@app.route('/auth/registrar', methods=['POST'])
def auth_registrar():
    dados = request.json or {}
    username = dados.get('username')
    email = dados.get('email')
    senha = dados.get('senha')

    if not username or not email or not senha:
        return jsonify({"sucesso": False, "mensagem": "Preencha todos os campos!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    user_existente = cursor.execute("SELECT * FROM usuarios WHERE email = ? OR username = ?", (email, username)).fetchone()
    if user_existente:
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Este e-mail ou utilizador já está registado!"}), 400

    senha_criptografada = generate_password_hash(senha)
    cursor.execute("INSERT INTO usuarios (username, email, senha, verificado, role) VALUES (?, ?, ?, 1, 'user')", (username, email, senha_criptografada))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    session['user_id'] = user_id
    session['username'] = username
    session['role'] = 'user'
    return jsonify({"sucesso": True, "mensagem": "Conta criada com sucesso!"})

@app.route('/auth/login', methods=['POST'])
def auth_login():
    dados = request.json or {}
    identificador = dados.get('identificador')
    senha = dados.get('senha')

    if not identificador or not senha:
        return jsonify({"sucesso": False, "mensagem": "Informe os dados de login!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM usuarios WHERE email = ? OR username = ?", (identificador, identificador)).fetchone()
    conn.close()

    if user and check_password_hash(user['senha'], senha):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role'] if 'role' in user.keys() else 'user'
        session['foto'] = user['foto'] if 'foto' in user.keys() else None
        return jsonify({"sucesso": True, "mensagem": "Login realizado com sucesso!"})
    else:
        return jsonify({"sucesso": False, "mensagem": "Utilizador ou senha incorretos!"}), 401

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    email = user_info['email']
    username = user_info['name']
    foto_url = user_info.get('picture', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()

    if not user:
        senha_dummy = secrets.token_hex(8)
        cursor.execute("INSERT INTO usuarios (username, email, senha, verificado, role, foto) VALUES (?, ?, ?, 1, 'user', ?)", (username, email, senha_dummy, foto_url))
        conn.commit()
        user_id = cursor.lastrowid
        role = 'user'
    else:
        user_id = user['id']
        username = user['username']
        role = user['role'] if 'role' in user.keys() else 'user'
        cursor.execute("UPDATE usuarios SET foto = ? WHERE id = ?", (foto_url, user_id))
        conn.commit()

    conn.close()
    session['user_id'] = user_id
    session['username'] = username
    session['role'] = role
    session['foto'] = foto_url
    return redirect(url_for('pacotes'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('pacotes'))

@app.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email = request.form.get("email")
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        
        if user:
            token = secrets.token_hex(16)
            expiracao = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("DELETE FROM recuperacao_senha WHERE user_id = ?", (user['id'],))
            cursor.execute("INSERT INTO recuperacao_senha (user_id, token, expiracao) VALUES (?, ?, ?)", (user['id'], token, expiracao))
            conn.commit()
            
            link_redefinicao = url_for('redefinir_senha', token=token, _external=True)
            print(f"\n[RECUPERAÇÃO DE SENHA] Link gerado para {email}: {link_redefinicao}\n")
            conn.close()
            
            return render_template("esqueci_senha.html", sucesso="Se o e-mail existir, foi gerado um link de recuperação na consola do servidor!")
        
        conn.close()
        return render_template("esqueci_senha.html", sucesso="Se o e-mail existir, foi gerado um link de recuperação na consola do servidor!")

    return render_template("esqueci_senha.html")

@app.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    rec = cursor.execute("SELECT * FROM recuperacao_senha WHERE token = ?", (token,)).fetchone()
    if not rec:
        conn.close()
        return "Link inválido ou expirado.", 400
        
    if datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') > rec['expiracao']:
        cursor.execute("DELETE FROM recuperacao_senha WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return "Este link de recuperação expirou.", 400

    if request.method == "POST":
        nova_senha = request.form.get("senha")
        if not nova_senha:
            conn.close()
            return render_template("redefinir_senha.html", erro="Informe a nova palavra-passe!")
            
        senha_criptografada = generate_password_hash(nova_senha)
        cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (senha_criptografada, rec['user_id']))
        cursor.execute("DELETE FROM recuperacao_senha WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        
        return redirect(url_for('pacotes'))

    conn.close()
    return render_template("redefinir_senha.html")


@app.route("/enviar_pedido", methods=["POST"])
def enviar_pedido():
    dados = request.json or {}
    nick = dados.get("nick")
    produto = dados.get("produto")
    preco = dados.get("preco")
    conta_entrega = dados.get("conta_entrega", "Não selecionada")
    
    if not nick:
        return jsonify({"sucesso": False, "mensagem": "Por favor, informe seu Nick!"}), 400

    user_id = session.get('user_id')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pedidos (user_id, nick_roblox, produto, preco, status) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, nick, produto, preco, "Pendente"))
        conn.commit()
        conn.close()
        
        payload = {
            "username": "Sniper Arena - Bot de Vendas",
            "embeds": [
                {
                    "title": "🛒 Novo Pedido Realizado!",
                    "color": 3066993,
                    "fields": [
                        {"name": "📦 Produto", "value": f"```{produto}```", "inline": True},
                        {"name": "💰 Valor", "value": f"```{preco}```", "inline": True},
                        {"name": "👤 Nick do Cliente", "value": f"```{nick}```", "inline": False},
                        {"name": "🎮 Conta Escolhida para Entrega", "value": f"```{conta_entrega}```", "inline": False}
                    ],
                    "footer": {
                        "text": "Sniper Arena Store — Sistema de Vendas Automático"
                    }
                }
            ]
        }

        if WEBHOOK_NOVOS_PEDIDOS:
            requests.post(WEBHOOK_NOVOS_PEDIDOS, json=payload)

        return jsonify({"sucesso": True, "mensagem": "Pedido registrado com sucesso!"}), 200
        
    except Exception as e:
        print(f"Erro ao processar pedido/webhook: {e}")
        return jsonify({"sucesso": False, "mensagem": f"Erro interno: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)