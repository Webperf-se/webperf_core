#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
import datetime as dt

db = SQLAlchemy()

class Sites(db.Model):
    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    website = db.Column(db.String(256))
    active = db.Column(db.SmallInteger, default=1)

    def __repr__(self):
        return '<Site %r>' % self.title

class SiteTests(db.Model):
    __tablename__ = 'sitetests'

    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    id = db.Column(db.Integer, primary_key=True)
    test_date = db.Column(db.DateTime)
    type_of_test = db.Column(db.SmallInteger, default=0)
    check_report = db.Column(db.Text)
    json_check_data = db.Column(db.Text)
    most_recent = db.Column(db.SmallInteger, default=1)
    rating = db.Column(db.String, default=-1) #rating from 1-5 on how good the results were

    def __repr__(self):
        return '<SiteTest %r>' % self.test_date