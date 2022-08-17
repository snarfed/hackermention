"""
TODO:
check HN API max id
"""
from datetime import datetime, timedelta
import logging
import urllib.parse

from cachetools import TTLCache
from flask import abort, Flask, request
from flask_caching import Cache
from granary import microformats2
from oauth_dropins.webutil import appengine_info, flask_util, util, webmention
from oauth_dropins.webutil.appengine_config import ndb_client, tasks_client
from oauth_dropins.webutil.appengine_info import APP_ID
from oauth_dropins.webutil.util import json_dumps, json_loads
from requests.exceptions import RequestException

from models import Config, Domain, Item, Webmention

DEADLINE = timedelta(minutes=9)
API_BASE = 'https://hacker-news.firebaseio.com/v0'
API_ITEM = f'{API_BASE}/item/%s.json'
HN_ITEM = 'https://news.ycombinator.com/item?id=%s'
HN_USER = 'https://news.ycombinator.com/user?id=%s'

top_level_cache = TTLCache(1_000_000, 60 * 60 * 24 * 365)  # 1y expiration
NONE = 0

util.set_user_agent('hackermention <https://hackermention.appspot.com/>')

# Flask app
app = Flask(__name__)
app.template_folder = './templates'
app.json.compact = False
app.config.update({
    'ENV': 'development' if appengine_info.DEBUG else 'production',
    'CACHE_TYPE': 'SimpleCache',
})
app.after_request(flask_util.default_modern_headers)
app.register_error_handler(Exception, flask_util.handle_exception)

app.wsgi_app = flask_util.ndb_context_middleware(app.wsgi_app, client=ndb_client)
cache = Cache(app)


def get_item(id):
    resp = util.requests_get(API_ITEM % id).json()
    if resp.get('error') or resp.get('dead'):
        logging.info(f'{id}: {resp}')
        return None

    return resp


def source_url(comment_id, story_id):
    return urllib.parse.urljoin(request.url, f'/item/{comment_id}?story={story_id}')


@app.route('/_ah/process', methods=['POST'])
def process():
    start = datetime.now()

    config = Config.query().get()
    id = config.last_id
    # id = 1251

    while True:
        if datetime.now() - start > DEADLINE:
            logging.info(f'hit {DEADLINE} deadline, shutting down')
            config.last_id = id
            config.put()

            tasks_client.create_task(
                parent=tasks_client.queue_path(APP_ID, 'us-central', 'default'),
                task={
                    'app_engine_http_request': {
                        'http_method': 'POST',
                        'relative_uri': '/_ah/process',
                    },
                })

            return ''

        _process_one(id)
        id += 1


def _process_one(id):
    item = get_item(id)
    if not item:
        return

    item.pop('kids', None)
    Item(id=id, json=json_dumps(item)).put()
    logging.info(f'{id}: {item}')
    if item.get('type') != 'comment':
        return

    comment = item
    top = top_level_cache.get(id)
    if not top:
        top = item
        while top and top.get('type') == 'comment':
            top = get_item(top['parent'])
        top_level_cache[id] = top or NONE

    if top in (None, NONE):
        return

    top.pop('kids', None)
    logging.info(f'top level item {top["id"]} {top}')
    url = top.get('url')
    if top.get('type') != 'story' or not url:
        return

    try:
        endpoint, resp = webmention.discover(url, cache=True)
    except (ValueError, RequestException):
        cache_key = webmention.endpoint_cache_key(url)
        logging.info(f'endpoint discovery failed, caching NONE for {cache_key}',
                     exc_info=True)
        with webmention.endpoint_cache_lock:
            webmention.endpoint_cache[cache_key] = webmention.NO_ENDPOINT
        return

    if endpoint in (None, webmention.NO_ENDPOINT):
        logging.info('No webmention endpoint')
        return

    source = source_url(id, top['id'])
    target = resp.url if resp else util.follow_redirects(url).url
    domain_str = util.domain_from_link(target)

    if resp:
        # discovered a new endpoint
        logging.info(f'Storing Domain {domain_str} {endpoint}')
        Domain(id=domain_str, endpoint=endpoint).put()

    logging.info(f'Sending webmention, {source} => {target}')
    wm = Webmention.get_or_insert(
        f'{source} {target}', source=source, target=target, comment_id=id,
        story_id=top['id'])

    try:
        resp = webmention.send(endpoint, source, target)
    except (ValueError, RequestException):
        logging.info('send failed', exc_info=True)
        return

    if resp.status_code == 201:
        logging.info(resp.headers.get('Location'))

    wm.status = 'complete'
    wm.put()


@app.route('/item/<id>')
@flask_util.cached(cache, timedelta(hours=1))
def item(id):
    comment = get_item(id)
    if not comment:
        return 'No such item, or error', 404
    elif comment['type'] != 'comment':
        return f'{comment["type"]} items not yet supported', 400

    comment_url = HN_ITEM % comment['id']

    story_id = request.values['story']
    story = get_item(story_id)
    if not story:
        return 'No such story id', 404

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
            {'url': source_url(comment['parent'], story_id)},
            {'url': HN_ITEM % comment['parent']},
            {'url': HN_ITEM % story_id},
            {'url': story.get('url')},
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
