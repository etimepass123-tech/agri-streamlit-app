import bcrypt
from db.db import get_connection

def verify_user(username: str, password: str):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT * FROM users WHERE username=%s",
        (username,)
    )
    user = cur.fetchone()
    conn.close()

    if not user:
        return None

    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user

    return None
