#!/usr/bin/env python
"""Sends webmentions for a set of source and target URLs.

https://webmention.net/draft/#sender-notifies-receiver

TODO: skip Bridgy Reddit users
"""
import argparse
import csv
import logging
from pathlib import Path
import queue
import sys
import threading

from oauth_dropins.webutil import util, webmention
from requests.exceptions import HTTPError

from discover import BLOCKLIST

NUM_THREADS = 20

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
csv.field_size_limit(sys.maxsize)
util.set_user_agent('hackermention <https://hackermention.appspot.com/>')

endpoints = {}  # maps domain to endpoint
webmentions = queue.Queue(1000000)  # (source URL, target URL) tuples
results = queue.Queue()      # (source URL, target URL, result string) tuples
sent = set()                 # (source URL, target URL) tuples

args = None  # populated in main()


def sender():
    while True:
        source, target, endpoint = webmentions.get()
        try:
            resp = webmention.send(endpoint, source, target)
            result = f'HTTP {resp.status_code} {resp.headers.get("Location", "")}'
        except ValueError as e:
            result = f'bad URL: {e}'
        except HTTPError as e:
            status = e.response.status_code
            body = e.response.text.replace('\n', ' ')[:500]
            result = f'HTTP {status} {body} {e.response.headers.get("Location", "")}'
        except BaseException as e:
            if util.is_connection_failure(e):
                result = f'connection failed: {e}'
            else:
                print('!!! Thread dying !!!', file=sys.stderr)
                raise

        logging.info(result)
        results.put((source, target, result))
        webmentions.task_done()


def writer():
    out = Path(args.output)
    if not out.exists():
        with open(args.output, 'w') as f:
            f.write('source,target,result\n')

    with open(out, 'a', newline='', buffering=1) as f:
        writer = csv.writer(f, dialect=csv.unix_dialect)
        while True:
            writer.writerow(results.get())
            results.task_done()


def main():
    parser = argparse.ArgumentParser(description='Send webmentions.')
    parser.add_argument('--endpoints', '-e', help='webmention endpoints CSV with domain,endpoint URL')
    parser.add_argument('--file', '-f', help='input CSV with source,target URLs')
    parser.add_argument('--output', '-o', help='output CSV with source,target,result')
    global args
    args = parser.parse_args()

    # read endpoints
    global endpoints
    with open(args.endpoints) as f:
        endpoints = dict(csv.reader(f))
    print(f'Loaded {len(endpoints)} existing endpoints from {args.endpoints}', flush=True)

    # read already sent webmentions
    with open(args.output) as f:
        for src, target, _ in csv.reader(f):
            sent.add((src, target))
    print(f'Loaded {len(sent)} already sent webmentions from {args.output}', flush=True)

    # start worker threads
    threading.Thread(target=writer, daemon=True).start()
    for i in range(NUM_THREADS):
        threading.Thread(target=sender, daemon=True).start()

    # enqueue webmentions
    input = sys.stdin if args.file in (None, '-') else open(args.file, newline='')
    unseen = set()  # domains that aren't in endpoints file
    with input as f:
        for row in csv.reader(f):
            row = tuple(row)
            if not row or row in sent:
                continue

            try:
                source, target = row
            except ValueError:
                logging.warning(f'target URL probably has quote: {row}', exc_info=True)
                continue

            domain = util.domain_from_link(target)
            if not domain or util.domain_or_parent_in(domain, BLOCKLIST):
                continue

            if domain not in endpoints:
                if domain not in unseen:
                    unseen.add(domain)
                    print(f'{domain} not in endpoints file!', file=sys.stderr)
                continue

            endpoint = endpoints[domain]
            if not endpoint:
                continue

            sent.add(row)
            webmentions.put((source, target, endpoint))

    webmentions.join()
    results.join()


if __name__ == '__main__':
    main()
