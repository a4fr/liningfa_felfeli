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
""")
        if sys.argv[1] == 'clone_db':
            create_database(Config.DB.name)

    #######################################################################
    else:
        test_create_database()
    print('Done! (%.1fs)' % (time.time()-time_start))
