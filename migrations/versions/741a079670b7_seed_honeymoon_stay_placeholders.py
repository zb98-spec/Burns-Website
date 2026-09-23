"""seed honeymoon stay placeholders

Revision ID: 741a079670b7
Revises: 7a73c41e612c
Create Date: 2026-09-23 12:00:00.000000

"""
from datetime import date, timedelta

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '741a079670b7'
down_revision = '7a73c41e612c'
branch_labels = None
depends_on = None

# (first_night, last_night, staying label, map pin name, lat, lng). Ranges
# are checkin-through-checkout, so a stay's last_night is the night before
# the next entry's first_night (the checkout day itself belongs to
# wherever that night is spent). Lake Garda's coordinates are a rough
# regional placeholder; the rest are geocoded from each property's own
# listed address.
STAYS = [
    (date(2026, 9, 22), date(2026, 9, 24), "Lake Garda", "Lake Garda", 45.4936, 10.6088),
    # Via Colleramole 59, Impruneta (Firenze) — per the property's own site.
    (date(2026, 9, 25), date(2026, 9, 27), "Dimora Ghirlandaio", "Dimora Ghirlandaio", 43.71650, 11.20829),
    # Localita Borgo Scopeto, Castelnuovo Berardenga (Siena) — geocoded.
    (date(2026, 9, 28), date(2026, 10, 1), "Borgo Scopeta", "Borgo Scopeta", 43.39249, 11.36936),
    (date(2026, 10, 2), date(2026, 10, 3), "Naples", "Naples", 40.8518, 14.2681),
    (date(2026, 10, 4), date(2026, 10, 5), "Palermo", "Palermo", 38.1157, 13.3615),
    (date(2026, 10, 6), date(2026, 10, 9), "Syracuse, Sicily", "Syracuse, Sicily", 37.0755, 15.2866),
    (date(2026, 10, 10), date(2026, 10, 10), "Catania", "Catania", 37.5079, 15.0830),
]


def _rows():
    for first_night, last_night, staying, location_name, lat, lng in STAYS:
        day = first_night
        while day <= last_night:
            yield day, staying, location_name, lat, lng
            day += timedelta(days=1)


def upgrade():
    honeymoon_days = sa.table(
        'honeymoon_days',
        sa.column('date', sa.Date()),
        sa.column('staying', sa.Text()),
        sa.column('location_name', sa.String()),
        sa.column('location_lat', sa.Float()),
        sa.column('location_lng', sa.Float()),
    )
    conn = op.get_bind()
    for day, staying, location_name, lat, lng in _rows():
        conn.execute(
            honeymoon_days.update()
            .where(honeymoon_days.c.date == day)
            .values(staying=staying, location_name=location_name, location_lat=lat, location_lng=lng)
        )
    # Oct 11 is the departure day (flying home from Catania) — no new
    # night's stay, per the itinerary schema's "N/A for departure days".
    conn.execute(
        honeymoon_days.update()
        .where(honeymoon_days.c.date == date(2026, 10, 11))
        .values(staying="N/A (departure day)")
    )


def downgrade():
    honeymoon_days = sa.table(
        'honeymoon_days',
        sa.column('date', sa.Date()),
        sa.column('staying', sa.Text()),
        sa.column('location_name', sa.String()),
        sa.column('location_lat', sa.Float()),
        sa.column('location_lng', sa.Float()),
    )
    conn = op.get_bind()
    conn.execute(
        honeymoon_days.update().values(
            staying=None, location_name=None, location_lat=None, location_lng=None
        )
    )
