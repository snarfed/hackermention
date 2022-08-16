"""Datastore models."""
from datetime import datetime, timedelta, timezone
import logging

from google.cloud import ndb
from oauth_dropins.webutil.models import StringIdModel

logger = logging.getLogger(__name__)


class Config(ndb.Model):
    """Singleton."""
    last_id = ndb.IntegerProperty(required=True)


class Webmention(StringIdModel):
    """Key id is '[source URL] [target URL]'.
    """
    comment_id = ndb.IntegerProperty(required=True)
    story_id = ndb.IntegerProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True, required=True, tzinfo=timezone.utc)
    updated = ndb.DateTimeProperty(auto_now=True, tzinfo=timezone.utc)
    status = ndb.StringProperty(choices=('complete','failed'))
