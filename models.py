"""Datastore models."""
from datetime import datetime, timedelta, timezone
import logging

from google.cloud import ndb
from oauth_dropins.webutil.models import StringIdModel


class Config(ndb.Model):
    """Singleton."""
    created = ndb.DateTimeProperty(auto_now_add=True, required=True, tzinfo=timezone.utc)
    updated = ndb.DateTimeProperty(auto_now=True, tzinfo=timezone.utc)
    last_id = ndb.IntegerProperty(required=True)


class Webmention(StringIdModel):
    """Key id is '[source URL] [target URL]'.
    """
    source = ndb.StringProperty(required=True)
    target = ndb.StringProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True, required=True, tzinfo=timezone.utc)
    updated = ndb.DateTimeProperty(auto_now=True, tzinfo=timezone.utc)
    comment_id = ndb.IntegerProperty(required=True)
    story_id = ndb.IntegerProperty(required=True)
    status = ndb.StringProperty(choices=('complete', 'failed'))


class Domain(StringIdModel):
    """Key id is full domain, including subdomain(s)."""
    created = ndb.DateTimeProperty(auto_now_add=True, required=True, tzinfo=timezone.utc)
    updated = ndb.DateTimeProperty(auto_now=True, tzinfo=timezone.utc)
    endpoint = ndb.StringProperty()


class Item(ndb.Model):
    json = ndb.TextProperty(required=True)


