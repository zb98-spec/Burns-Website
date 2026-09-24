from datetime import date, datetime

from app.extensions import db


class Bottle(db.Model):
    __tablename__ = "wine_bottles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    producer = db.Column(db.String(200))
    vintage = db.Column(db.Integer)
    varietal = db.Column(db.String(200))
    region = db.Column(db.String(200))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    location = db.Column(db.String(200))
    purchase_price = db.Column(db.Numeric(10, 2))
    purchase_date = db.Column(db.Date)
    purchase_source = db.Column(db.String(200))
    drink_window_start = db.Column(db.Integer)
    drink_window_end = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def drink_status(self):
        """Returns 'cellar', 'ready', 'past', or None if no window is set."""
        if self.drink_window_start is None or self.drink_window_end is None:
            return None
        current_year = date.today().year
        if current_year < self.drink_window_start:
            return "cellar"
        if current_year > self.drink_window_end:
            return "past"
        return "ready"


class TastingHistory(db.Model):
    __tablename__ = "wine_tasting_history"

    id = db.Column(db.Integer, primary_key=True)
    bottle_id = db.Column(
        db.Integer, db.ForeignKey("wine_bottles.id", ondelete="SET NULL")
    )
    # Snapshot of the wine's identity at the time it was drunk, so history
    # stays meaningful even if the bottle entry is later edited or deleted.
    wine_name = db.Column(db.String(200), nullable=False)
    producer = db.Column(db.String(200))
    vintage = db.Column(db.Integer)
    consumed_date = db.Column(db.Date, default=date.today, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text)
    image = db.Column(db.LargeBinary)
    image_mimetype = db.Column(db.String(100))

    bottle = db.relationship("Bottle")
    scores = db.relationship(
        "TastingScore", backref="tasting", cascade="all, delete-orphan"
    )

    @property
    def average_score(self):
        if not self.scores:
            return None
        return sum(s.score for s in self.scores) / len(self.scores)


class TastingScore(db.Model):
    __tablename__ = "wine_tasting_scores"

    id = db.Column(db.Integer, primary_key=True)
    tasting_id = db.Column(
        db.Integer,
        db.ForeignKey("wine_tasting_history.id", ondelete="CASCADE"),
        nullable=False,
    )
    taster_name = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer, nullable=False)
