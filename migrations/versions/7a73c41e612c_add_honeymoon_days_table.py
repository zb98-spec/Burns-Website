"""add honeymoon days table

Revision ID: 7a73c41e612c
Revises: 57808958d92e
Create Date: 2026-09-23 00:00:00.000000

"""
from datetime import date, timedelta

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a73c41e612c'
down_revision = '57808958d92e'
branch_labels = None
depends_on = None

TRIP_START = date(2026, 9, 22)
TRIP_END = date(2026, 10, 11)


def upgrade():
    honeymoon_days = op.create_table('honeymoon_days',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('staying', sa.Text(), nullable=True),
    sa.Column('travel', sa.Text(), nullable=True),
    sa.Column('breakfast', sa.Text(), nullable=True),
    sa.Column('lunch', sa.Text(), nullable=True),
    sa.Column('dinner', sa.Text(), nullable=True),
    sa.Column('activities', sa.Text(), nullable=True),
    sa.Column('location_name', sa.String(length=200), nullable=True),
    sa.Column('location_lat', sa.Float(), nullable=True),
    sa.Column('location_lng', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('date')
    )

    day_count = (TRIP_END - TRIP_START).days + 1
    op.bulk_insert(honeymoon_days, [
        {'date': TRIP_START + timedelta(days=offset)}
        for offset in range(day_count)
    ])


def downgrade():
    op.drop_table('honeymoon_days')
