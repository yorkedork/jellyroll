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

from jellyroll.backends.item.models import Item
from jellyroll.backends.search.models import SearchEngine, WebSearch, WebSearchResult
from jellyroll.providers import utils, register_provider, gdata 
from jellyroll.providers import ProviderException, StructuredDataProvider

RSS_URL = "https://%s:%s@www.google.com/searchhistory/?output=rss"
VIDEO_TAG_URL = "http://video.google.com/tags?docid=%s"


class GoogleSearchProvider(StructuredDataProvider):
    """

    
    """
    def __init__(self):
        super(GoogleSearchProvider,self).__init__()

        self.search_engine = SearchEngine.objects.get(name="Google")
        self.register_model(WebSearch, priority=0)
        self.register_model(WebSearchResult, priority=1)

        feed_url = RSS_URL % (settings.GOOGLE_USERNAME,settings.GOOGLE_PASSWORD)
        self.register_data_url(WebSearch,feed_url,'rss')
        self.register_data_url(WebSearchResult,feed_url,'rss')
        
    def enabled(self):
        ok = hasattr(settings, 'GOOGLE_USERNAME') and hasattr(settings, 'GOOGLE_PASSWORD')
        if not ok:
            log.warn('The Google Search provider is not available because the '
                     'GOOGLE_USERNAME and/or GOOGLE_PASSWORD settings are '
                     'undefined.')
        return ok

    def source_id(self, model_cls, extra):
        if model_cls == WebSearch:
            return ":".join( [extra['engine'].name,extra['query'],extra['guid']] ) 
        elif model_cls == WebSearchResult:
            return md5.new( extra['url'] ).hexdigest()

    def get_default_fields(self, model_cls):
        fields = super(GoogleSearchProvider,self).get_default_fields(model_cls)
        if model_cls == WebSearchResult:
            for field in fields:
                if field.name == 'search':
                    fields.remove(field)
                    break

        return fields

    def update_websearch(self, data_iterator):
        websearch_list = self.incoming["websearch"] = list()
        for entry in data_iterator:
            if entry.tags[0].term != "web query":
                continue

            obj = {}

            obj['engine'] = self.search_engine
            obj['guid'] = smart_unicode(urlparse.urlsplit(entry.guid)[2].replace("/searchhistory/", ""))
            obj['query'] = smart_unicode(entry.title)
            obj['timestamp'] = datetime.datetime(tzinfo=tzinfo.FixedOffset(0), *entry.updated_parsed[:6])

            websearch_list.append( obj )

    def update_websearchresult(self, data_iterator):
        websearchresult_list = self.incoming["websearchresult"] = list()
        for entry in data_iterator:
            if entry.tags[0].term != "web result":
                continue

            obj = {}

            obj['guid'] = smart_unicode(entry.query_guid)
            obj['title'] = smart_unicode(entry.title)
            obj['url'] = smart_unicode(entry.link)

            websearchresult_list.append( obj )

    def pre_handle_item_created(self, model_instance, data):
        if model_instance.__class__ == WebSearchResult:
            try:
                ct = ContentType.objects.get_for_model(WebSearch)
                websearch = Item.objects.filter(content_type=ct).\
                    get(source_id__endswith=":".join( [data['guid']] ))
                model_instance.search = websearch.object
            except Item.DoesNotExist:
                raise ProviderException( \
                    "Could not find WebSearch given by guid %s" % \
                        data['guid'])

register_provider( GoogleSearchProvider )
