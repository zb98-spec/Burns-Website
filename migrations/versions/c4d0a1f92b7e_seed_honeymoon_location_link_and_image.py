"""seed honeymoon location link and image

Revision ID: c4d0a1f92b7e
Revises: b2c918e04f6a
Create Date: 2026-09-23 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d0a1f92b7e'
down_revision = 'b2c918e04f6a'
branch_labels = None
depends_on = None

# (location_name, website, static image path). Images are self-hosted
# stock photos of each place (Wikimedia Commons, CC-licensed) as
# placeholders until real trip photos replace them.
LOCATIONS = [
    ("Lake Garda", "https://www.visitgarda.com/en/garda_lake/", "/static/images/honeymoon/lake-garda.jpg"),
    ("Dimora Ghirlandaio", "https://dimoraghirlandaio.it/en/", "/static/images/honeymoon/tuscany-chianti.jpg"),
    ("Borgo Scopeta", "https://www.borgoscopetorelais.it/en/relais-chianti-tuscany", "/static/images/honeymoon/tuscany-chianti.jpg"),
    ("Naples", "https://www.italia.it/en/campania/naples", "/static/images/honeymoon/naples.jpg"),
    ("Palermo", "https://www.visitsicily.info/en/localita/palermo/", "/static/images/honeymoon/palermo.jpg"),
    ("Syracuse, Sicily", "https://www.visitsicily.info/en/localita/siracusa/", "/static/images/honeymoon/syracuse.jpg"),
    ("Catania", "https://www.visit-catania.com/en", "/static/images/honeymoon/catania.jpg"),
]


def upgrade():
    honeymoon_days = sa.table(
        'honeymoon_days',
        sa.column('location_name', sa.String()),
        sa.column('location_url', sa.String()),
        sa.column('location_image_url', sa.String()),
    )
    conn = op.get_bind()
    for name, url, image_url in LOCATIONS:
        conn.execute(
            honeymoon_days.update()
            .where(honeymoon_days.c.location_name == name)
            .values(location_url=url, location_image_url=image_url)
        )


def downgrade():
    honeymoon_days = sa.table(
        'honeymoon_days',
        sa.column('location_url', sa.String()),
        sa.column('location_image_url', sa.String()),
    )
    conn = op.get_bind()
    conn.execute(
        honeymoon_days.update().values(location_url=None, location_image_url=None)
    )
