# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, tzinfo

# from trac.util.datefmt(0.11)

def to_datetime(t, tzinfo=None):
    if t is None:
        return datetime.now(localtz)
    elif isinstance(t, datetime):
        return t
    elif isinstance(t, (int,long,float)):
        return datetime.fromtimestamp(t, tzinfo or localtz)
    raise TypeError('expecting datetime, int, long, float, or None; got %s' % type(t))

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self._offset = timedelta(minutes=offset)
        self.zone = name

    def __str__(self):
        return self.zone

    def __repr__(self):
        return '<FixedOffset "%s" %s>' % (self.zone, self._offset)

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self.zone

    def dst(self, dt):
        return _zero

utc = FixedOffset(0, 'UTC')
_zero = timedelta(0)

