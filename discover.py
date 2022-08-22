#!/usr/bin/env python
"""Discovers webmention endpoints for a set of input target URLs.

https://webmention.net/draft/#sender-discovers-receiver-webmention-endpoint
"""
import argparse
import csv
import logging
from pathlib import Path
import queue
import sys
import threading

from oauth_dropins.webutil import util
from oauth_dropins.webutil.webmention import discover
from requests.exceptions import RequestException

NUM_THREADS = 50

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

endpoints = {}  # maps domain to endpoint
endpoints_lock = threading.RLock()
targets = queue.Queue()     # target URLs
discovered = queue.Queue()  # (domain, endpoint) tuples

parser = argparse.ArgumentParser(description='Discover webmention endpoints.')
parser.add_argument('--file', '-f', help='input CSV with source,target URLs')
parser.add_argument('--output', '-o', help='output CSV with domain,endpoint')
args = parser.parse_args()


def discoverer():
    while True:
        target = targets.get()
        domain = util.domain_from_link(target)
        if not domain:
            targets.task_done()
            continue

        if domain not in endpoints:
            try:
                endpoint, _ = discover(target)
            except BaseException as e:
                if (isinstance(e, (ValueError, RequestException)) or
                    util.is_connection_failure(e)):
                    endpoint = None
                else:
                    print('!!! Thread dying !!!')
                    raise
                logging.warning(target, exc_info=True)

            with endpoints_lock:
                endpoints[domain] = endpoint

            discovered.put((domain, endpoint))

        targets.task_done()


def writer():
    with open(args.output, 'a', newline='', buffering=1) as f:
        writer = csv.writer(f, dialect=csv.unix_dialect)
        while True:
            writer.writerow(discovered.get())
            discovered.task_done()


def main():
    # read existing endpoints, if any
    outpath = Path(args.output)
    if outpath.exists():
        for row in csv.reader(open(outpath)):
            endpoints[row[0]] = row[1]
        print(f'Loaded {len(endpoints)} existing endpoints from {args.output}')
    else:
        with open(outpath, 'a') as outf:
            outf.write('domain,endpoint\n')

    # start worker threads
    threading.Thread(target=writer, daemon=True).start()
    for i in range(NUM_THREADS):
        threading.Thread(target=discoverer, daemon=True).start()

    # enqueue new endpoints
    input = sys.stdin if args.file in (None, '-') else open(args.file, newline='')
    with input as f:
        for row in csv.reader(f):
            if row:
                targets.put(row[1])

    targets.join()
    discovered.join()


if __name__ == '__main__':
    main()
