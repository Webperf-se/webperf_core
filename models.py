#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
import datetime as dt

db = SQLAlchemy()

class Sites(db.Model):
    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    date_added = db.Column(db.DateTime)
    category = db.Column(db.SmallInteger, default=0)
    public = db.Column(db.SmallInteger, default=1)
    quota = db.Column(db.SmallInteger, default=1)
    rating_overall = db.Column(db.Numeric, default=-1)
    rating_pagespeed = db.Column(db.Numeric, default=-1)
    rating_usability = db.Column(db.Numeric, default=-1)
    rating_a11y = db.Column(db.Numeric, default=-1)
    slug = db.Column(db.String(120), unique=1)
    website = db.Column(db.String(256))
    date_modified = db.Column(db.DateTime)
    premium = db.Column(db.SmallInteger, default=0)
    active = db.Column(db.SmallInteger, default=1)
    #tests = db.relationship('Test', backref='site')

    def __repr__(self):
        return '<Site %r>' % self.title

class SiteTests(db.Model):
    __tablename__ = 'sitetests'

    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    id = db.Column(db.Integer, primary_key=True)
    test_date = db.Column(db.DateTime)
    pages_checked = db.Column(db.Integer, default=1)
    type_of_test = db.Column(db.SmallInteger, default=0)
    check_report = db.Column(db.Text)
    json_check_data = db.Column(db.Text)
    most_recent = db.Column(db.SmallInteger, default=1)
    rating = db.Column(db.Numeric, default=-1) #rating from 1-5 on how good the results were

    def __repr__(self):
        return '<SiteTest %r>' % self.test_date

class SiteConfig(db.Model):
    __tablename__ = 'siteconfig'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    key = db.Column(db.String(100))
    value = db.Column(db.Text)
    date_modified = db.Column(db.DateTime, default=dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

class ErrorLog(db.Model):
    __tablename__ = 'errorlog'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    notes = db.Column(db.String(100), default='')
    error_mess = db.Column(db.Text, default='')
    date_modified = db.Column(db.DateTime, default=dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

class TestData(db.Model):
    __tablename__ = 'testdata'
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    url = db.Column(db.Text)
    batch_id = db.Column(db.Integer)
    tested_yet = db.Column(db.SmallInteger, default=0)
    summarized_yet = db.Column(db.SmallInteger, default=0)
    type_of_test = db.Column(db.Integer, default=0)
    value_num = db.Column(db.Numeric, default=-1)
    value_string = db.Column(db.Text, default='')
    rating = db.Column(db.Numeric, default=-1)
    json_result = db.Column(db.Text, default='')
    test_date = db.Column(db.DateTime, default=dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

class Categories(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    description = db.Column(db.Text)
    rating_overall = db.Column(db.Numeric, default=-1)
    rating_a11y = db.Column(db.Numeric, default=-1)
    rating_pagespeed = db.Column(db.Numeric, default=-1)
    rating_usability = db.Column(db.Numeric, default=-1)
    rating_webstandard = db.Column(db.Numeric, default=-1)
    slug = db.Column(db.String(128))
    public = db.Column(db.Numeric, default=1)

    def __repr__(self):
        return '<Category %r>' % self.title

class Articles(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    slug = db.Column(db.String(128))
    feat_image = db.Column(db.String(128))
    feat_image_square = db.Column(db.String(128))
    description = db.Column(db.String(260))
    date_added = db.Column(db.DateTime)
    content = db.Column(db.Text)
    content_type = db.Column(db.SmallInteger, default=0) #0 = blogpost, 1 = report
    related_site_id = db.Column(db.Text) # innehållet kan antingen vara en siffra eller [siffror,med,komma]
    related_cat_id = db.Column(db.Text) # innehållet kan antingen vara en siffra eller [siffror,med,komma]

    def __repr__(self):
        return '<Article %r>' % self.title

#db.create_all()