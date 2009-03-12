import datetime
import logging
log = logging.getLogger("jellyroll.providers.lastfm")
import md5

from httplib2 import HttpLib2Error
from django.conf import settings
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.functional import memoize
from django.utils.http import urlquote
from django.utils.encoding import smart_str, smart_unicode

from jellyroll.backends.item.models import Item
from jellyroll.backends.track.models import Track
from jellyroll.providers import utils, register_provider, StructuredDataProvider

RECENT_TRACKS_URL = "http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.xml?limit=100"
TRACK_TAGS_URL    = "http://ws.audioscrobbler.com/1.0/track/%s/%s/toptags.xml"
ARTIST_TAGS_URL   = "http://ws.audioscrobbler.com/1.0/artist/%s/toptags.xml"


class LastfmProvider(StructuredDataProvider):
    """
    

    """
    def __init__(self):
        super(LastfmProvider,self).__init__()

        self.register_model(Track)
        self.register_data_url(Track,RECENT_TRACKS_URL%settings.LASTFM_USERNAME,"xml")

    def enabled(self):
        ok = hasattr(settings, 'LASTFM_USERNAME')
        if not ok:
            log.warn('The Last.fm provider is not available because the '
                     'LASTFM_USERNAME settings is undefined.')
        return ok

    def source_id(self, model_cls, extra):
        return md5.new(smart_str(extra['artist_name']) + \
                           smart_str(extra['track_name']) + \
                           str(extra['timestamp'])).hexdigest()

    def tags_for_track(self, artist_name, track_name):
        """
        Get the top tags for a track. Also fetches tags for the artist. Only
        includes tracks that break a certain threshold of usage, defined by
        settings.LASTFM_TAG_USAGE_THRESHOLD (which defaults to 15).
        """
        
        urls = [
            ARTIST_TAGS_URL % (urlquote(artist_name)),
            TRACK_TAGS_URL % (urlquote(artist_name), urlquote(track_name)),
            ]
        tags = set()
        for url in urls:
            tags.update(self.tags_for_url(url))
        
    def tags_for_url(self, url):
        tags = set()
        try:
            xml = utils.getxml(url)
        except HttpLib2Error, e:
            if e.code == 408:
                return ""
            else:
                raise
        except SyntaxError:
            return ""
        for t in xml.getiterator("tag"):
            count = utils.safeint(t.find("count").text)
            if count >= getattr(settings, 'LASTFM_TAG_USAGE_THRESHOLD', 15):
                tag = slugify(smart_unicode(t.find("name").text))
                tags.add(tag[:50])

        return tags

    # Memoize tags to avoid unnecessary API calls.
    tag_cache = {}
    tags_for_url = memoize(tags_for_url, tag_cache, 1)

    def update_track(self, data_iterator_func):
        last_update_date = Item.objects.get_last_update_of_model(Track)
        log.debug("Last update date: %s", last_update_date)
    
        tracks = self.incoming["track"] = list()
        for track in data_iterator_func("track"):

            # date delivered as UTC
            timestamp = datetime.datetime.fromtimestamp(int(track.find('date').get('uts')))
            if utils.JELLYROLL_ADJUST_DATETIME:
                timestamp = utils.utc_to_local_timestamp(int(track.find('date').get('uts')))

            artist = track.find('artist')

            obj = {}
            obj['artist_name'] = smart_unicode(artist.text)
            obj['artist_mbid'] = artist.get('mbid')
            obj['track_name']  = smart_unicode(track.find('name').text)
            obj['track_mbid']  = smart_unicode(track.find('mbid').text)

            obj['tags']        = self.tags_for_track(obj['artist_name'], obj['track_name'])
            obj['url']         = smart_unicode(track.find('url').text)
            obj['timestamp']   = timestamp

            tracks.append( obj )

register_provider( LastfmProvider )
