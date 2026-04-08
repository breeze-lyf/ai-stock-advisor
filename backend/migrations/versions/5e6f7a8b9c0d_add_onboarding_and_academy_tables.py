"""add_onboarding_and_academy_tables

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e6f7a8b9c0d'
down_revision: Union[str, None] = '4d5e6f7a8b9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建用户投资画像表
    op.create_table(
        'user_investment_profiles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('risk_tolerance', sa.String(length=20), nullable=False, default='MODERATE'),
        sa.Column('risk_tolerance_score', sa.Integer(), nullable=False, default=5),
        sa.Column('investment_experience', sa.String(length=50), nullable=False, default='BEGINNER'),
        sa.Column('investment_years', sa.Integer(), nullable=True),
        sa.Column('preferred_markets', sa.String(length=200), nullable=True),
        sa.Column('default_market', sa.String(length=10), nullable=False, default='US'),
        sa.Column('investment_style', sa.String(length=50), nullable=True),
        sa.Column('investment_horizon', sa.String(length=20), nullable=True),
        sa.Column('portfolio_size', sa.String(length=20), nullable=True),
        sa.Column('target_annual_return', sa.Numeric(5, 2), nullable=True),
        sa.Column('notification_preferences', sa.String(length=100), nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_investment_profiles_user_id'), 'user_investment_profiles', ['user_id'], unique=True)

    # 创建用户仪表盘配置表
    op.create_table(
        'user_dashboard_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('layout_config', sa.JSON(), nullable=True),
        sa.Column('theme', sa.String(length=20), nullable=False, default='light'),
        sa.Column('color_scheme', sa.String(length=20), nullable=True),
        sa.Column('show_portfolio_summary', sa.Boolean(), nullable=False, default=True),
        sa.Column('show_market_overview', sa.Boolean(), nullable=False, default=True),
        sa.Column('show_ai_signals', sa.Boolean(), nullable=False, default=True),
        sa.Column('show_news_feed', sa.Boolean(), nullable=False, default=True),
        sa.Column('show_watchlist', sa.Boolean(), nullable=False, default=True),
        sa.Column('default_view', sa.String(length=20), nullable=False, default='dashboard'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_dashboard_configs_user_id'), 'user_dashboard_configs', ['user_id'], unique=True)

    # 创建投资课程表
    op.create_table(
        'investment_courses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('difficulty', sa.String(length=20), nullable=False, default='BEGINNER'),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False, default=60),
        sa.Column('total_lessons', sa.Integer(), nullable=False, default=0),
        sa.Column('total_points', sa.Integer(), nullable=False, default=0),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('is_published', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建投资课程章节表
    op.create_table(
        'investment_lessons',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('course_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('video_url', sa.String(length=500), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False, default=10),
        sa.Column('points', sa.Integer(), nullable=False, default=10),
        sa.Column('has_quiz', sa.Boolean(), nullable=False, default=True),
        sa.Column('quiz_passing_score', sa.Integer(), nullable=False, default=70),
        sa.Column('quiz_questions', sa.JSON(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investment_lessons_course_id'), 'investment_lessons', ['course_id'], unique=False)

    # 创建用户学习进度表
    op.create_table(
        'user_education_progress',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('course_id', sa.String(), nullable=False),
        sa.Column('lesson_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='NOT_STARTED'),
        sa.Column('progress_percent', sa.Integer(), nullable=False, default=0),
        sa.Column('quiz_score', sa.Integer(), nullable=True),
        sa.Column('quiz_passed', sa.Boolean(), nullable=True),
        sa.Column('quiz_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('time_spent_minutes', sa.Integer(), nullable=False, default=0),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_education_progress_user_id'), 'user_education_progress', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_education_progress_course_id'), 'user_education_progress', ['course_id'], unique=False)
    op.create_index(op.f('ix_user_education_progress_lesson_id'), 'user_education_progress', ['lesson_id'], unique=False)

    # 添加外键约束
    op.create_foreign_key(
        'fk_user_investment_profiles_user',
        'user_investment_profiles',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_dashboard_configs_user',
        'user_dashboard_configs',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_investment_lessons_course',
        'investment_lessons',
        'investment_courses',
        ['course_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_education_progress_user',
        'user_education_progress',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_education_progress_course',
        'user_education_progress',
        'investment_courses',
        ['course_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_education_progress_lesson',
        'user_education_progress',
        'investment_lessons',
        ['lesson_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # 删除外键约束
    op.drop_constraint('fk_user_education_progress_lesson', 'user_education_progress', type_='foreignkey')
    op.drop_constraint('fk_user_education_progress_course', 'user_education_progress', type_='foreignkey')
    op.drop_constraint('fk_user_education_progress_user', 'user_education_progress', type_='foreignkey')
    op.drop_constraint('fk_investment_lessons_course', 'investment_lessons', type_='foreignkey')
    op.drop_constraint('fk_user_dashboard_configs_user', 'user_dashboard_configs', type_='foreignkey')
    op.drop_constraint('fk_user_investment_profiles_user', 'user_investment_profiles', type_='foreignkey')

    # 删除索引
    op.drop_index(op.f('ix_user_education_progress_lesson_id'), table_name='user_education_progress')
    op.drop_index(op.f('ix_user_education_progress_course_id'), table_name='user_education_progress')
    op.drop_index(op.f('ix_user_education_progress_user_id'), table_name='user_education_progress')
    op.drop_index(op.f('ix_investment_lessons_course_id'), table_name='investment_lessons')
    op.drop_index(op.f('ix_user_dashboard_configs_user_id'), table_name='user_dashboard_configs')
    op.drop_index(op.f('ix_user_investment_profiles_user_id'), table_name='user_investment_profiles')

    # 删除表
    op.drop_table('user_education_progress')
    op.drop_table('investment_lessons')
    op.drop_table('investment_courses')
    op.drop_table('user_dashboard_configs')
    op.drop_table('user_investment_profiles')
