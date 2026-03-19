"""split analysis report scope

Revision ID: 2f4d6b8c9a10
Revises: ae1b8335eea2
Create Date: 2026-03-19 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f4d6b8c9a10"
down_revision: Union[str, Sequence[str], None] = "ae1b8335eea2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_reports",
        sa.Column("report_scope", sa.String(), nullable=False, server_default="user_interaction"),
    )
    op.create_index(
        "ix_analysis_reports_ticker_scope_model_created",
        "analysis_reports",
        ["ticker", "report_scope", "model_used", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_reports_user_scope_created",
        "analysis_reports",
        ["user_id", "report_scope", "created_at"],
        unique=False,
    )

    op.execute(
        """
        UPDATE analysis_reports
        SET report_scope = 'shared_stock_analysis'
        WHERE CAST(input_context_snapshot AS TEXT) LIKE '%"analysis_scope": "stock_shared"%'
        """
    )

    op.alter_column("analysis_reports", "user_id", existing_type=sa.String(), nullable=True)

    op.execute(
        """
        UPDATE analysis_reports
        SET user_id = NULL
        WHERE report_scope = 'shared_stock_analysis'
        """
    )
    op.alter_column("analysis_reports", "report_scope", server_default=None)


def downgrade() -> None:
    op.execute(
        """
        UPDATE analysis_reports
        SET report_scope = 'user_interaction'
        WHERE report_scope = 'shared_stock_analysis'
        """
    )
    op.alter_column("analysis_reports", "user_id", existing_type=sa.String(), nullable=False)
    op.drop_index("ix_analysis_reports_user_scope_created", table_name="analysis_reports")
    op.drop_index("ix_analysis_reports_ticker_scope_model_created", table_name="analysis_reports")
    op.drop_column("analysis_reports", "report_scope")
