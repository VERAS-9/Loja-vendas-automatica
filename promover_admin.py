import sqlite3

# Conecta à tua base de dados
conn = sqlite3.connect('banco.db')
cursor = conn.cursor()

# Altera o utilizador para admin (Substitui 'TeuNick' pelo teu nome de utilizador no site)
nome_usuario = 'GIVANILSON Lima'

cursor.execute("UPDATE usuarios SET role = 'admin' WHERE username = ?", (nome_usuario,))
conn.commit()

# Verifica se funcionou
usuario = cursor.execute("SELECT username, role FROM usuarios WHERE username = ?", (nome_usuario,)).fetchone()
conn.close()

if usuario:
    print(f"Sucesso! O utilizador '{usuario[0]}' agora tem a role: '{usuario[1]}'")
else:
    print("Utilizador não encontrado. Verifica se escreveste o nome exatamente igual.")