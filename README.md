# hackermention

Universal [webmention](https://webmention.net/) [backfeed](https://indieweb.org/backfeed) for [Hacker News](https://news.ycombinator.com/), using the [Hacker News Firebase API](https://github.com/HackerNews/API).

This project is placed into the public domain.

TODO:
* Indie Map domains
* find false negatives
  * eg tantek.com, *.micro.blog
* remove false positives from endpoints.csv
  * hostnames with no TLDs
  * ...?
* HN 2016-present (BQ only has 2006-2016)

# Projects

## Hacker News service

TODO

## Command line discoverer and sender

`discover.py` reads a CSV of `source,target` URLs and attempts to discover the target URL's webmention endpoint. It writes the results as a `domain,endpoint` CSV.

`send.py` reads a CSV of `source,target` URLs from stdin and attempts to send a webmention for each pair. It writes the results as a `source,target,result` CSV.


## Sites

### Hacker News

The [BigQuery archive](https://console.cloud.google.com/bigquery?p=bigquery-public-data&d=hacker_news&page=dataset) is based on the [Hacker News Firebase API](https://github.com/HackerNews/API).

First, query the [BigQuery dataset](https://console.cloud.google.com/bigquery?p=bigquery-public-data&d=hacker_news&page=dataset) for story URLs:

```sql
#standardSQL
SELECT stories.id, stories.url
FROM `bigquery-public-data.hacker_news.stories` AS stories
WHERE stories.url IS NOT NULL
```

Download the results as CSV to Google Drive, then download locally, then run this to convert the ids to URLs:

```sh
sed -i'' -e 's/^[0-9]/https:\/\/news.ycombinator.com\/item\?id=&/' [filename]
```

Then, run `discover.py`

```sh
./discover.py -o ~/endpoints.csv -f ~/hn_wms.csv >hn_wms.log 2>&1

./send.py -e ~/endpoints.csv -o ~/results.hn.csv -f ~/hn_wms.csv >results.hn.log 2>&1
```

Stats:
* 2006 - 2016
* 1_840_154 posts
* 207_441_982 bytes

### Reddit

[pushshift.io's Reddit archive](https://files.pushshift.io/reddit/) has dumps of submissions and comments

Files are [Zstandard-compressed](https://facebook.github.io/zstd/) [JSON Lines](https://jsonlines.org/), and must be decompressed with `zstd --long=31 ...`](https://files.pushshift.io/reddit/submissions/README.txt).

```sh
# discover endpoints
zstd --long=31 -cd RS_*.zst \
  | jq -j '"https://www.reddit.com", .permalink, ",\"", .url, "\"\n"' \
  | tr -d '\000' \
  | sed 's/\\&amp\\;/\\&/' \
  | grep -Ev ',https://([^.]+\.)?(redd\.it|reddit\.com)/' \
  | grep -Ev '\.(avi|gif|gifv|jpg|jpeg|mov|mp4|pdf|png)$' \
  | ./discover.py -o ~/endpoints.csv >discover.log 2>&1 &

# send webmentions
zstd --long=31 -cd RS_*.zst \
  | jq -j '"https://www.reddit.com", .permalink, ",\"", .url, "\"\n"' \
  | tr -d '\000' \
  | sed 's/\\&amp\\;/\\&/' \
  | grep -Ev ',https://([^.]+\.)?(redd\.it|reddit\.com)/' \
  | grep -Ev '\.(avi|gif|gifv|jpg|jpeg|mov|mp4|pdf|png)$' \
  | ./send.py -e ~/endpoints.csv -o ~/results.reddit.csv
```

Stats:

* 6/2005 - 7/2022
* 193 months
* 3_836_796_818_274 bytes
* 1_344_306_994 submissions (posts)

### Bridgy

Query the [BigQuery dataset](https://console.cloud.google.com/bigquery?ws=%211m5%211m4%214m3%211sbrid-gy%212sdatastore%213sResponse) for `Response.sent` URLs:

```sql
#standardSQL
SELECT '', s
from `brid-gy.datastore.Response` r, r.sent s
```

Then download the results as CSV locally.

### Indie Map

TODO

### IndieWeb wiki chat-names and users

Download [https://indieweb.org/chat-names](https://indieweb.org/chat-names), remove header and footer HTML around list of links, then run this to extract URLs:

```sh
grep -E -o 'href="http[^"]+' chat-names.html | cut -c 7-
```
