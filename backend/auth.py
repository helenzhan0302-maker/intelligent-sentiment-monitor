"""v0.4.0 认证模块: SQLite 持久化 + JWT + 邀请码 + 搜索历史"""
import os
import uuid
import json
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

# ── JWT 密钥管理 ──────────────────────────────────────────────
def _get_jwt_secret() -> str:
    """从 .env 读取或生成 JWT_SECRET"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    secret = os.getenv("JWT_SECRET", "")
    if secret:
        return secret
    # 首次生成，写入 .env
    secret = secrets.token_hex(32)
    with open(env_path, "a") as f:
        f.write(f"\nJWT_SECRET={secret}\n")
    # 更新环境变量（当前进程生效）
    os.environ["JWT_SECRET"] = secret
    print("[Auth] Generated new JWT_SECRET and saved to .env")
    return secret


JWT_SECRET = _get_jwt_secret()
JWT_EXPIRY_HOURS = 24 * 7  # 7 天
JWT_ALGORITHM = "HS256"

# ── 预置邀请码 ──────────────────────────────────────────────────
PRESEED_INVITE_CODES = ["DEMO2026", "VIBECODE", "MONITOR01"]


# ── 数据库初始化 ───────────────────────────────────────────────
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """建表 + 预置邀请码"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invite_codes (
            code TEXT PRIMARY KEY,
            is_used INTEGER DEFAULT 0,
            used_by TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            keywords TEXT NOT NULL,
            results_json TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_history_user
            ON search_history(user_id, created_at DESC);
    """)

    # Seed 邀请码（幂等）
    for code in PRESEED_INVITE_CODES:
        conn.execute(
            "INSERT OR IGNORE INTO invite_codes (code) VALUES (?)",
            (code,),
        )

    conn.commit()
    conn.close()
    print("[Auth] Database initialized.")


# ── 密码哈希 ───────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"pbkdf2:sha256:100000${salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algo, salt, dk_hex = hashed.rsplit("$", 2)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# ── JWT Token ──────────────────────────────────────────────────
def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── 用户操作 ───────────────────────────────────────────────────
def register_user(username: str, password: str, invite_code: str) -> dict:
    """注册成功返回 {user_id, username}，失败抛异常"""
    conn = _get_conn()

    # 验证邀请码（可复用，不限次数）
    row = conn.execute(
        "SELECT code FROM invite_codes WHERE code = ?",
        (invite_code.upper().strip(),),
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError("邀请码无效")

    # 检查用户名唯一
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError("用户名已存在")

    user_id = str(uuid.uuid4())
    pwd_hash = hash_password(password)

    conn.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        (user_id, username, pwd_hash),
    )
    conn.commit()
    conn.close()

    return {"user_id": user_id, "username": username}


def login_user(username: str, password: str) -> dict:
    """登录成功返回 {token, user_id, username}，失败抛异常"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if not row:
        raise ValueError("用户名或密码错误")
    if not verify_password(password, row["password_hash"]):
        raise ValueError("用户名或密码错误")

    token = create_token(row["id"])
    return {
        "token": token,
        "user_id": row["id"],
        "username": row["username"],
    }


# ── 搜索历史 CRUD ──────────────────────────────────────────────
def save_search(user_id: str, keywords: list[str], results_json: str) -> str:
    """保存搜索记录，返回 history_id"""
    history_id = str(uuid.uuid4())
    conn = _get_conn()
    conn.execute(
        "INSERT INTO search_history (id, user_id, keywords, results_json) VALUES (?, ?, ?, ?)",
        (history_id, user_id, json.dumps(keywords, ensure_ascii=False), results_json),
    )
    conn.commit()
    conn.close()
    return history_id


def get_history(user_id: str, limit: int = 20) -> list[dict]:
    """获取搜索历史列表"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, keywords, created_at FROM search_history "
        "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "keywords": json.loads(r["keywords"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_history_detail(user_id: str, history_id: str) -> dict | None:
    """获取单条搜索历史详情（含完整结果）"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM search_history WHERE id = ? AND user_id = ?",
        (history_id, user_id),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "keywords": json.loads(row["keywords"]),
        "results": json.loads(row["results_json"]),
        "created_at": row["created_at"],
    }
