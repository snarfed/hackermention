#!/usr/bin/env python
"""Sends webmentions for a set of source and target URLs.

https://webmention.net/draft/#sender-notifies-receiver
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

NUM_THREADS = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

endpoints = {}  # maps domain to endpoint
webmentions = queue.Queue()  # (source URL, target URL) tuples
results = queue.Queue()      # (source URL, target URL, result string) tuples

parser = argparse.ArgumentParser(description='Send webmentions.')
parser.add_argument('--endpoints', '-e', help='webmention endpoints CSV with domain,endpoint URL')
parser.add_argument('--file', '-f', help='input CSV with source,target URLs')
parser.add_argument('--output', '-o', help='output CSV with source,target,result')
args = parser.parse_args()


def sender():
    while True:
        row = webmentions.get()
        # try:
        source, target = row
        # except:
        #     print('@', row)
        #     raise
        domain = util.domain_from_link(target)

        if domain not in endpoints:
            if domain:
                print(f'{domain} not in endpoints file!', file=sys.stderr)
            webmentions.task_done()
            continue
            # sys.exit(1)

        endpoint = endpoints[domain]
        if not endpoint:
            webmentions.task_done()
            continue

        try:
            resp = webmention.send(endpoint, source, target)
            result = f'HTTP {resp.status_code} {resp.text} {resp.headers.get("Location", "")}'
        except ValueError as e:
            result = f'bad URL: {e}'
        except HTTPError as e:
            status = e.response.status_code
            result = f'HTTP {status} {e.response.text} {e.response.headers.get("Location", "")}'
        except BaseException as e:
            if util.is_connection_failure(e):
                result = f'connection failed: {e}'
            else:
                print('!!! Thread dying !!!', file=sys.stderr)
                raise
        finally:
            logging.warning(webmention, exc_info=True)

        results.put((source, target, result))
        webmentions.task_done()


def writer():
    out = Path(args.output)
    if not out.exists():
        with open(args.output, 'w') as f:
            f.write('source,target,result\n')

    with open(out, 'a', newline='', buffering=1) as f:
        writer = csv.writer(f, dialect=csv.unix_dialect)
        writer.writerow(('source', 'target', 'result'))
        while True:
            writer.writerow(results.get())
            results.task_done()


def main():
    # read endpoints
    with open(args.endpoints) as f:
        for domain, endpoint in csv.reader(f):
            endpoints[domain] = endpoint
    print(f'Loaded {len(endpoints)} existing endpoints from {args.endpoints}', flush=True)

    # start worker threads
    threading.Thread(target=writer, daemon=True).start()
    for i in range(NUM_THREADS):
        threading.Thread(target=sender, daemon=True).start()

    # enqueue webmentions
    input = sys.stdin if args.file in (None, '-') else open(args.file, newline='')
    with input as f:
        for row in csv.reader(f):
            if row:
                webmentions.put(row)

    webmentions.join()
    results.join()


if __name__ == '__main__':
    main()
