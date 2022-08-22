# hackermention

Universal [webmention](https://webmention.net/) [backfeed](https://indieweb.org/backfeed) for [Hacker News](https://news.ycombinator.com/), using the [Hacker News Firebase API](https://github.com/HackerNews/API).

This project is placed into the public domain.


# Projects

## Hacker News service

TODO

## Command line discoverer and sender

`discover.py` reads a CSV of `source,target` URLs and attempts to discover the target URL's webmention endpoint. It writes the results as a `domain,endpoint` CSV.

`send.py` reads a CSV of `source,target` URLs from stdin and attempts to send a webmention for each pair. It writes the results as a `source,target,result` CSV.


## Extractors

### Hacker News

The [BigQuery archive](https://console.cloud.google.com/bigquery?p=bigquery-public-data&d=hacker_news&page=dataset) is based on the [Hacker News Firebase API](https://github.com/HackerNews/API).

### Reddit

[pushshift.io's Reddit archive](https://files.pushshift.io/reddit/) has dumps of submissions and comments

Files are [Zstandard-compressed](https://facebook.github.io/zstd/) [JSON Lines](https://jsonlines.org/), and must be decompressed with `zstd --long=31 ...`](https://files.pushshift.io/reddit/submissions/README.txt).

```sh
zstd --long=31 -cd RS_2022-06.zst \
  | jq -j '"https://www.reddit.com", .permalink, ",", .url, "\n"' \
  | sed 's/\\&amp\\;/\\&/' \
  | grep -Ev ',https://([^.]+\.)?(redd\.it|reddit\.com)/' \
  | grep -Ev '\.(avi|gif|gifv|jpg|jpeg|mov|mp4|pdf|png)$' \
  | ./discover.py -f ~/RS_2022-07.csv -o ~/endpoints.csv >discover.log 2>&1 &
```

STATE: currently running RS_2022-06
