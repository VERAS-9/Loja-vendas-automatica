import sqlite3

conn = sqlite3.connect('banco.db')
cursor = conn.cursor()

# Mostra a estrutura da tabela chat_pedidos
cursor.execute("PRAGMA table_info(chat_pedidos);")
colunas = cursor.fetchall()

print("--- Colunas da tabela chat_pedidos ---")
for coluna in colunas:
    print(f"Nome: {coluna[1]} | Tipo: {coluna[2]}")

conn.close()