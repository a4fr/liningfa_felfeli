from pprint import pprint
import time
import sqlite3
from sqlite3 import Error
import Config
import sys


class SQLCommands:
    tables = {
        """
CREATE TABLE IF NOT EXISTS "images" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"lining_url"	TEXT NOT NULL UNIQUE,
	"liningfa_url"	TEXT,
	"last_update"	TEXT
);""",
        """
CREATE TABLE IF NOT EXISTS "details" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"lining_pid"	INTEGER NOT NULL UNIQUE,
	"liningfa_pid"	INTEGER,
	"json"	TEXT,
	"last_update"	TEXT
);"""}
    indexs = [
        """
CREATE INDEX "lining_pid_index_details" ON "details" (
	"lining_pid"
);""",
        """
CREATE INDEX "lining_url_index_images" ON "images" (
	"lining_url"
);"""
    ]


def create_database(db_name='felfeli.db'):
    """ Create felfeli database """
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        print('Database (%s) created!' % db_name)

        print('Creating tables...')
        for sql in SQLCommands.tables:
            print(sql)
            c.execute(sql)

        print('Creating indexes...')
        for sql in SQLCommands.indexs:
            print(sql)
            c.execute(sql)
        conn.commit()
    except Error as e:
        print('Error:', e)
    finally:
        conn.close()


def query_on_database(db_name='felfeli.db', unlimited_times=True):
    """ Run query on database and show results
    :param db_name: str
    :param unlimited_times: get and run query unlimited times
    :return:
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    while True:
        query = input('Enter SQL: ')
        c.execute(query)
        results = c.fetchall()
        pprint(results)
        if not unlimited_times:
            break
    conn.close()


def test_query_on_database():
    query_on_database(
        db_name=Config.DB.name,
        unlimited_times=True
    )


def test_create_database():
    create_database('felfeli_test.db')


if __name__ == '__main__':
    time_start = time.time()
    if len(sys.argv) >= 2:
        if sys.argv[1] == 'help':
            print("""database_manager.py [command]
    help                Show this help
    clone_db            Create felfeli.db database, create tables and indexes
    insert_test_rows    Insert a few rows to database for testing scripts
    query               Run query and print results
""")
        if sys.argv[1] == 'clone_db':
            create_database(Config.DB.name)
        elif sys.argv[1] == 'query':
            test_query_on_database()

    #######################################################################
    else:
        test_create_database()
    print('Done! (%.1fs)' % (time.time()-time_start))
