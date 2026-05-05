
import asyncio
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy.future import select

async def reset():
    async with SessionLocal() as db:
        stmt = select(User).where(User.email == "haha@qq.com")
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            print(f"Resetting password for {user.email}")
            user.hashed_password = get_password_hash("123456")
            await db.commit()
            print("✅ Password reset to '123456'")
        else:
            print("❌ User not found")

if __name__ == "__main__":
    asyncio.run(reset())
