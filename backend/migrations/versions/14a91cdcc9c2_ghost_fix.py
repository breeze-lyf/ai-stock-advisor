"""ghost fix for 14a91cdcc9c2

Revision ID: 14a91cdcc9c2
Revises: 877955ab3cd8
Create Date: 2026-03-15 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14a91cdcc9c2'
down_revision: Union[str, Sequence[str], None] = '877955ab3cd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 这是一个桩文件，用于让 Alembic 识别线上数据库中已存在的幽灵版本号 14a91cdcc9c2
    # 该版本在本地代码库中缺失，将其挂载到当前 Head (877955ab3cd8) 之后
    pass


def downgrade() -> None:
    pass
