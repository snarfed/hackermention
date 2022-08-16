"""Request handlers.
"""
import logging
import urllib.parse

from flask import abort, Flask, request
from granary import microformats2
from oauth_dropins.webutil import appengine_info, flask_util, util, webmention
from oauth_dropins.webutil.appengine_config import ndb_client

from models import Config, Webmention

logger = logging.getLogger(__name__)
util.set_user_agent('hackermention <https://hackermention.appspot.com/>')

HN_BASE = 'https://hacker-news.firebaseio.com/v0'
HN_ITEM = f'{HN_BASE}/item/%s.json'
HN_USER = 'https://news.ycombinator.com/user?id=%s'

# Flask app
app = Flask(__name__)
app.template_folder = './templates'
app.json.compact = False
app.config['ENV'] = 'development' if appengine_info.DEBUG else 'production'
app.after_request(flask_util.default_modern_headers)
app.register_error_handler(Exception, flask_util.handle_exception)

app.wsgi_app = flask_util.ndb_context_middleware(app.wsgi_app, client=ndb_client)


def get_item(id):
    resp = util.requests_get(HN_ITEM % id).json()
    if resp.get('error') or resp.get('dead'):
        logging.info(f'{id}: {resp}')
        return None

    return resp


def item_url(id):
    return urllib.parse.urljoin(request.url, f'/item/{id}')


@app.route('/_ah/process')
def process():
    # config = Config.query().get()
    # id = config.last_id + 1
    id = 28

    for id in range(28, 1000):
        item = get_item(id)
        logging.info(f'{id}: {item}')
        if not item or item['type'] != 'comment':
            continue

        comment = item
        while item and item['type'] == 'comment':
            item = get_item(item['parent'])

        if not item:
            continue

        logging.info(f'top level item {item["id"]} {item["type"]}')
        if item['type'] != 'story':
            continue

        endpoint, resp = webmention.discover(item['url'])
        if endpoint:
            source = item_url(id)
            logging.info(f'Sending webmention, {source} => {resp.url}')
            # TODO: catch HTTP errors
            webmention.send(endpoint, source, resp.url)
        else:
            logging.info('No webmention endpoint')

    return ''


@app.route('/item/<id>')
def item(id):
    target = request.values['target']

    comment = get_item(id)
    if not comment:
        return 'No such item, or error', 404
    elif comment['type'] != 'comment':
        return f'{comment["type"]} items not yet supported', 400

    comment_url = item_url(comment['id'])

    html = microformats2.object_to_html({
        'objectType': 'comment',
        'id': f'tag:news.ycombinator.com:{id}',
        'url': comment_url,
        'content': comment['text'],
        'published': util.maybe_timestamp_to_iso8601(comment['time']),
        'author': {
            'displayName': comment['by'],
            'url': HN_USER % comment['by'],
        },
        'inReplyTo': [
            {'url': item_url(comment['parent'])},
            {'url': target},
        ],
    })
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0;url={comment_url}">
</head>
<body>
{html}
</body>
</html>
"""


@app.route('/_ah/<any(start, stop, warmup):_>')
def noop(_):
  return 'OK'
