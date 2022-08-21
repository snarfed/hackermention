#!/usr/bin/env python
"""Discovers webmention endpoints for a set of input target URLs.

https://webmention.net/draft/#sender-discovers-receiver-webmention-endpoint
"""
import argparse
import csv
import logging
from pathlib import Path
import sys

from oauth_dropins.webutil import util
from oauth_dropins.webutil.webmention import discover
from requests.exceptions import RequestException

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def main():
    parser = argparse.ArgumentParser(description='Discover webmention endpoints.')
    parser.add_argument('--file', '-f', help='input CSV with source,target URLs')
    parser.add_argument('--output', '-o', help='output CSV with domain,endpoint')
    args = parser.parse_args()

    endpoints = {}  # maps domain to endpoint

    # read existing endpoints, if any
    outpath = Path(args.output)
    if outpath.exists():
        for row in csv.reader(open(outpath)):
            endpoints[row[0]] = row[1]
        print(f'Loaded {len(endpoints)} existing endpoints from {args.output}')
    else:
        with open(outpath, 'a') as outf:
            outf.write('domain,endpoint\n')

    # discover new endpoints
    with open(args.file, newline='') as inf, \
         open(outpath, 'a', newline='', buffering=1) as outf:
        writer = csv.writer(outf, dialect=csv.unix_dialect)
        r = csv.reader(inf)
        for source, target in csv.reader(inf):
            domain = util.domain_from_link(target)
            if domain not in endpoints:
                try:
                    endpoint, _ = discover(target)
                except BaseException as e:
                    if (isinstance(e, (ValueError, RequestException)) or
                        util.is_connection_failure(e)):
                        endpoint = None
                    else:
                        raise
                    logging.warning(f'{target}', exc_info=True)
                endpoints[domain] = endpoint
                writer.writerow((domain, endpoint))


if __name__ == '__main__':
    main()
