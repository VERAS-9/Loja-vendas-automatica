import sqlite3

def inicializar_banco():
    # Isso vai criar um arquivo chamado 'banco.db' automaticamente na pasta do projeto
    conexao = sqlite3.connect('banco.db')
    cursor = conexao.cursor()

    # 1. Tabela de Usuários (Clientes e Administradores)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            discord_id TEXT,
            verificado INTEGER DEFAULT 0,
            codigo_verificacao TEXT,
            role TEXT DEFAULT 'cliente'
        )
    ''')

    # 2. Tabela de Pedidos (Vinculada ao Usuário que comprou)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nick_roblox TEXT NOT NULL,
            produto TEXT NOT NULL,
            preco TEXT NOT NULL,
            status TEXT DEFAULT 'Pendente',
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios (id)
        )
    ''')

    conexao.commit()
    conexao.close()
    print("✅ Banco de dados 'banco.db' criado e inicializado com sucesso!")

if __name__ == '__main__':
    inicializar_banco()