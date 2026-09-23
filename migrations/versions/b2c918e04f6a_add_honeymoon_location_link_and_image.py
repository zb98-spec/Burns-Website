"""add honeymoon location link and image

Revision ID: b2c918e04f6a
Revises: 741a079670b7
Create Date: 2026-09-23 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c918e04f6a'
down_revision = '741a079670b7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('honeymoon_days', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('location_image_url', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('honeymoon_days', schema=None) as batch_op:
        batch_op.drop_column('location_image_url')
        batch_op.drop_column('location_url')
