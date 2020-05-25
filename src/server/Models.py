from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False,
                     default=datetime.utcnow().date())


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)


class ServiceDesk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    token = db.Column(db.String(254), nullable=True)


class Service_ServiceDesk(db.Model):
    service_id = db.Column(db.Integer, db.ForeignKey('Service.id'),
                           nullable=False, primary_key=True)
    service_desk_id = db.Column(db.Integer, db.ForeignKey('ServiceDesk.id'),
                                nullable=False, primary_key=True)


class Service_Tickets(db.Model):
    service_id = db.Column(db.Integer, db.ForeignKey('Service.id'),
                           nullable=False, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('Ticket.id'),
                          nullable=False, primary_key=True)
