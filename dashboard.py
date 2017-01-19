import os
import logging
import logging.config
from logging import handlers
import sqlite3
import json
import requests
from cli.client import DrasticClient
from contextlib import closing
from flask import Flask, jsonify, request, session, g, redirect, url_for, render_template, flash


app = Flask(__name__)
app.config.from_object(__name__)
app.logger.setLevel(logging.DEBUG)
handler = handlers.RotatingFileHandler(
  os.path.join(app.instance_path, 'dashboard.log'),
  maxBytes=1024 * 1024 * 100,
  backupCount=20)
app.logger.addHandler(handler)

app.config.update(dict(
    DATABASE=os.path.join(app.instance_path, 'dashboard.db'),
    DEBUG=True,
    USERNAME='admin',
    PASSWORD='default',
    SECRET_KEY='INSECURE_DEVELOPMENT_KEY',
    PROPAGATE_EXCEPTIONS=True
))

drastic_url = os.getenv('DRASTIC_URL', 'http://localhost')
drastic_user = os.getenv('DRASTIC_USER', 'worker')
drastic_password = os.getenv('DRASTIC_PASSWORD', 'password')
ciber_http_over_ftp_url = os.getenv('FTP_OVER_HTTP_URL', 'http://localhost')


def get_client():
    global __client
    if __client is None:
        myclient = DrasticClient(drastic_url)
        res = myclient.authenticate(drastic_user, drastic_password)
        if not res.ok():
            raise IOError("Drastic authentication failed: {0}".format(res.msg()))
        __client = myclient
    return __client


@app.errorhandler(404)
def page_not_found(error):
    return 'This route does not exist {}'.format(request.url), 404


def connect_db():
    """Connects to the specific database."""
    logging.info(str(app.config['DATABASE']))
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


@app.cli.command()
def init_db():
    db = get_db()
    with app.open_instance_resource('dashboard.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()
    logging.warn('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    # db = getattr(g, '_database', None)
    # if db is None:
    #    db = g._database = connect_db()
    # return db
    return connect_db()


# @app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/dashboard/')
def welcome():
    return render_template('dashboard.html')


@app.route('/dashboard/httpftp_rgroups/', methods=['GET'])
def get_httpftp_recordgroups():
    res = requests.get('{0}/Federal Record Groups/'.format(ciber_http_over_ftp_url))
    return jsonify(res.json())


@app.route('/dashboard/drastic_rgroups/', methods=['GET'])
def get_drastic_rgroups():
    return get_drastic_path('/NARA')


def get_drastic_path(path):
    path = path[:-1] if path.endswith('?') else path

    res = get_client().ls(path)
    if res.code() in [404, 403]:  # object probably deleted
        logging.warn("Dropping task for an object that gives a 403/403: {0}".format(path))
        return
    if not res.ok():
        raise IOError(str(res))

    return jsonify(res.json())


@app.route('/dashboard/rgroup_ingest/')
def collections():
    return render_template('dashboard.html')


if __name__ == '__main__':
    app.run("0.0.0.0", processes=5)
