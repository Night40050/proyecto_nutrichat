from .database import db
from datetime import datetime

class UserProduct(db.Model):
    __tablename__ = 'user_products'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='General')
    notes = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    source = db.Column(db.String(50), default='manual')
    unit = db.Column(db.String(20), default='unidades')
    quantity = db.Column(db.Integer, default=1)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserProduct {self.name}>'

class ScrapingSession(db.Model):
    __tablename__ = 'scraping_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), nullable=False)
    session_id = db.Column(db.String(50), unique=True, nullable=False)
    total_products = db.Column(db.Integer, default=0)
    total_value = db.Column(db.Float, default=0.0)
    new_products = db.Column(db.Integer, default=0)
    updated_products = db.Column(db.Integer, default=0)
    mode = db.Column(db.String(20), default='auto')
    category = db.Column(db.Integer, default=1)
    category_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<ScrapingSession {self.session_id}>'