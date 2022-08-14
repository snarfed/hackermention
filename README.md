# hackermention

Universal [webmention](https://webmention.net/) [backfeed](https://indieweb.org/backfeed) for [Hacker News](https://news.ycombinator.com/).

Uses the [Hacker News Firebase API](https://github.com/HackerNews/API) to trigger a [Firebase Cloud Function](https://firebase.google.com/docs/functions) on every new comment that sends a webmention to the story's URL. Includes a separate function that serves Hacker News comments as HTML with microformats2.

Uses [AJ Jordan](https://strugee.net/)'s [node-send-webmention](https://github.com/strugee/node-send-webmention) library.

This project is placed into the public domain.
