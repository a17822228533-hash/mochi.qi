import sqlite3
import os

DATA_DIR = '/root/mochi'
DB_PATH = f'{DATA_DIR}/mochi.db'

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 用户表
c.execute('''CREATE TABLE IF NOT EXISTS users (
    uid TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    human_name TEXT DEFAULT '用户',
    call_name TEXT DEFAULT '老公',
    is_admin INTEGER DEFAULT 0,
    created REAL NOT NULL
)''')

# 邀请码表
c.execute('''CREATE TABLE IF NOT EXISTS invites (
    code TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0,
    used_by TEXT,
    created REAL NOT NULL
)''')

# 帖子表
c.execute('''CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    uid TEXT NOT NULL,
    author TEXT NOT NULL,
    is_ai INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    time INTEGER NOT NULL
)''')

# 点赞表
c.execute('''CREATE TABLE IF NOT EXISTS likes (
    post_id TEXT NOT NULL,
    uid TEXT NOT NULL,
    PRIMARY KEY (post_id, uid)
)''')

# 评论表
c.execute('''CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    uid TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    time INTEGER NOT NULL
)''')

conn.commit()
conn.close()

print(f'Database initialized: {DB_PATH}')
