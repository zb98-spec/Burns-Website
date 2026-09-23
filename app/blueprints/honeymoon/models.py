from app.extensions import db


class Day(db.Model):
    __tablename__ = "honeymoon_days"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)

    # The six fixed itinerary fields, always in this order.
    staying = db.Column(db.Text)
    travel = db.Column(db.Text)
    breakfast = db.Column(db.Text)
    lunch = db.Column(db.Text)
    dinner = db.Column(db.Text)
    activities = db.Column(db.Text)

    # Where this night's stay pins on the route map. Left blank until an
    # admin fills it in; days without coordinates are skipped on the map.
    location_name = db.Column(db.String(200))
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    location_url = db.Column(db.String(500))
    location_image_url = db.Column(db.String(500))
