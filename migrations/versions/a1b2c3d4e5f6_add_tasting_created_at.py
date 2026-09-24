"""add tasting history created_at timestamp

Revision ID: a1b2c3d4e5f6
Revises: c4d0a1f92b7e
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'c4d0a1f92b7e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'wine_tasting_history',
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    with op.batch_alter_table('wine_tasting_history') as batch_op:
        batch_op.alter_column('created_at', server_default=None)


def downgrade():
    op.drop_column('wine_tasting_history', 'created_at')
