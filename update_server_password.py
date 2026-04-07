#!/usr/bin/env python3
"""Update test user password on server"""
import subprocess
import sys

python_code = '''
import asyncio
import asyncpg
from passlib.context import CryptContext

async def main():
    conn = await asyncpg.connect(
        "postgresql://ai_stock_app:KfZpdJdl7PsVlEJfij7oBZLb@host.docker.internal:5432/ai_stock_advisor"
    )

    # Generate new hash
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("test123456")

    # Update
    await conn.execute(
        """
        UPDATE users SET hashed_password = $1 WHERE email = $2
        """,
        hashed,
        "test@qq.com"
    )

    # Verify
    result = await conn.fetchval(
        "SELECT hashed_password FROM users WHERE email = $1",
        "test@qq.com"
    )

    print(f"Updated hash length: {len(result)}")
    print(f"Hash starts with: {result[:30]}...")

    await conn.close()
    print("Success!")

asyncio.run(main())
'''

# Write to server and execute
ssh_cmd = [
    "ssh", "-i", "/Users/breeze/.ssh/key.pem", "-o", "StrictHostKeyChecking=no",
    "root@47.100.109.73",
    f"docker exec stock_backend python -c {repr(python_code)}"
]

result = subprocess.run(ssh_cmd, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr, file=sys.stderr)
sys.exit(result.returncode)
