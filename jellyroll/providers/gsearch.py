import feedparser
import datetime
import dateutil
import urlparse
# Monkeypatch feedparser to understand smh:query_guid elements
feedparser._FeedParserMixin._start_smh_query_guid = lambda self, attrs: self.push("query_guid", 1)
import logging
log = logging.getLogger("jellyroll.providers.gsearch")
import md5

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import tzinfo
from django.utils.encoding import smart_unicode

from jellyroll.core.models import Item
from jellyroll.contrib.search.models import SearchEngine, WebSearch, WebSearchResult
from jellyroll.providers import utils, register_provider, gdata 
from jellyroll.providers import ProviderException, StructuredDataProvider

RSS_URL = "https://%s:%s@www.google.com/searchhistory/?output=rss"
VIDEO_TAG_URL = "http://video.google.com/tags?docid=%s"


class GoogleSearchProvider(StructuredDataProvider):
    """

    
    """
    MODELS = [
        'search.WebSearch',
        'search.WebSearchResult',
        'search.SearchEngine',
        ]

    def __init__(self):
        super(GoogleSearchProvider,self).__init__()

        self.search_engine = SearchEngine.objects.get(name="Google")
        self.register_model(WebSearch, priority=0)

        feed_url = RSS_URL % (settings.GOOGLE_USERNAME,settings.GOOGLE_PASSWORD)
        self.register_data_url(WebSearch,feed_url,'rss')

        self.websearch_results = list()
        
    def enabled(self):
        ok = hasattr(settings, 'GOOGLE_USERNAME') and hasattr(settings, 'GOOGLE_PASSWORD')
        if not ok:
            log.warn('The Google Search provider is not available because the '
                     'GOOGLE_USERNAME and/or GOOGLE_PASSWORD settings are '
                     'undefined.')
        return ok

    def source_id(self, model_cls, extra):
        return ":".join( [extra['engine'].name,extra['query'],extra['guid']] ) 

    def update_websearch(self, data_iterator):
        websearch_list = self.incoming["websearch"] = list()
        for entry in data_iterator:
            if entry.tags[0].term == "web query":
                obj = {}
                obj['engine'] = self.search_engine
                obj['guid'] = smart_unicode(urlparse.urlsplit(entry.guid)[2].replace("/searchhistory/", ""))
                obj['query'] = smart_unicode(entry.title)
                obj['timestamp'] = datetime.datetime(tzinfo=tzinfo.FixedOffset(0), *entry.updated_parsed[:6])

                websearch_list.append( obj )

            elif entry.tags[0].term == "web result":
                obj = {}
                obj['guid'] = smart_unicode(entry.query_guid)
                obj['title'] = smart_unicode(entry.title)
                obj['url'] = smart_unicode(entry.link)
                
                self.websearch_results.append( obj )

    def post_handle_default(self, model_instance, model_str, model_cls, data, created):
        results = [ result for result in self.websearch_results if result['guid'] == data['guid'] ]
        for result_data in results:
            result,created = WebSearchResult.objects.get_or_create(
                title = result_data['title'],
                url = result_data['url'],
                search = model_instance
                )

register_provider( GoogleSearchProvider )
