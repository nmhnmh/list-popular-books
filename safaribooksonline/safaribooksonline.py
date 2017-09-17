#!/usr/bin/env python3

import os
import calendar
import feedparser
import sqlite3
import re
from datetime import datetime, timedelta, timezone
from time import time
import argparse
from collections import namedtuple
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
FEED_URL = 'https://www.safaribooksonline.com/feeds/recently-added.rss'
FEED_DB_PATH = os.path.join(ROOT_DIR, '.database', 'weekly-books.sqlite')
FEED_DB_TABLE = 'safari_new_books'
WEEKLY_OUT_PATH = os.path.join(ROOT_DIR, '.build')
jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(ROOT_DIR, 'templates')),
    autoescape=select_autoescape(['html', 'xml'])
)


def save_new_entries(entries, db):
    iso_now = datetime.now(timezone.utc)
    iso_year, iso_week, iso_day = iso_now.isocalendar()
    '''
    Save each entry into database, transform and convert the field value if necessary.
    '''
    def find_entry_cover(links):
        '''
        find the enclusure(usually an image) link inside a bunch of links
        '''
        for l in links:
            if l.rel == 'enclosure' and re.match('image/', l.type):
                return l
    c = db.cursor()
    for e in entries:
        author_pub = re.match('(.*)\((.+)\)', e.author)
        if author_pub:
            author = author_pub.group(1).strip()
            publisher = author_pub.group(2).strip()
        else:
            author = ''
            publisher = e.author
        topics = ', '.join([t.term for t in e.tags])
        enclosure = find_entry_cover(e.links)
        isbn_match = re.search(r'\/view\/[^/]+\/([^/]+)\/?$', e.id)
        isbn = isbn_match.group(1)
        entry_data = (
            e.id,
            isbn,
            e.title,
            e.language,
            enclosure.href,
            topics,
            author,
            publisher,
            e.summary,
            e.content[0].value,
            e.published,
            calendar.timegm(e.published_parsed),
            int(iso_year),
            int(iso_week),
            int(iso_day),
            0,
            time()
        )
        c.execute('insert or ignore into safari_new_books(id, isbn, title, language, cover, topic, authors, publisher, summary, content, pub_date, pub_ts, iso_year, iso_week, iso_day, used, create_ts) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', entry_data)

def check_sqlite_table(db):
    '''
    Check if the database table presents in the database, if not create it.
    '''
    c = db.cursor()
    c.execute("select * from sqlite_master where type='table' and name=?", (FEED_DB_TABLE, ))
    tables = c.fetchall()
    if len(tables)<1:
        c.execute('''
            CREATE TABLE %s (
                id text unique,
                isbn text,
                title text,
                language text,
                cover text,
                topic text,
                authors text,
                publisher text,
                summary text,
                content text,
                pub_date text,
                pub_ts int,
                iso_year int,
                iso_week int,
                iso_day int,
                used int,
                create_ts int
            );
        ''' % FEED_DB_TABLE)

def fetch_and_save_new_books():
    '''
    Download newly added items feed from safari books website.
    Parse it and save entries inside to the database.
    '''
    feed = feedparser.parse(FEED_URL)
    db = sqlite3.connect(FEED_DB_PATH)
    check_sqlite_table(db)
    print("The feed has %d entries!" % len(feed.entries))
    if feed.entries and len(feed.entries)>0:
        save_new_entries(feed.entries, db)
    db.commit()
    db.close()

def generate_weekly_new_book_page():
    ''' Generate report for weekly new books '''
    iso_now = datetime.now(timezone.utc)
    iso_year, iso_week, iso_day = iso_now.isocalendar()
    week_year_name = "%dW%d.html" % (iso_year, iso_week)
    db = sqlite3.connect(FEED_DB_PATH)
    c = db.cursor()
    fields = [
        'id',
        'isbn',
        'title',
        'language',
        'cover',
        'topic',
        'authors',
        'publisher',
        'summary',
        'content',
        'pub_ts',
        'iso_year',
        'iso_week',
    ]
    filed_str = ', '.join(fields)
    c.execute('select ' + filed_str + ' from safari_new_books where iso_year=? and iso_week=? order by pub_ts desc', (iso_year, iso_week))
    Entry = namedtuple('Entry', fields)
    entries = c.fetchall()
    allbooks = list(map(Entry._make, entries))
    template = jinja_env.get_template('default.html')
    with open(os.path.join(ROOT_DIR, WEEKLY_OUT_PATH, week_year_name), 'w', encoding='utf8') as f:
        f.write(template.render({'title': 'Safari Books Online {0} Week{1} New Books'.format(iso_year, iso_week), 'books': allbooks}))
    # write this page as index.html as well
    with open(os.path.join(ROOT_DIR, WEEKLY_OUT_PATH, 'index.html'), 'w', encoding='utf8') as f:
        f.write(template.render({'title': 'Safari Books Online {0} Week{1} New Books'.format(iso_year, iso_week), 'books': allbooks}))
    db.commit()
    db.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Safari Books CLI")
    parser.add_argument('operation', help="the name of desired operation")
    args = parser.parse_args()
    operation = args.operation
    if operation in ['fetch', 'f']:
        fetch_and_save_new_books()
    elif operation in ['generate', 'gen', 'g']:
        generate_weekly_new_book_page()
    else:
        print("Unsupported operation: %s!" % operation)
