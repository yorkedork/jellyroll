import dateutil.parser
import dateutil.tz
import logging
log = logging.getLogger("jellyroll.providers.delicious")
import urllib
import time

from django.conf import settings
from django.db import transaction
from django.utils.encoding import smart_unicode

from jellyroll.core.models import Item
from jellyroll.contrib.bookmark.models import Bookmark
from jellyroll.providers import utils, register_provider, StructuredDataProvider


class DeliciousClient(object):
    """
    A super-minimal delicious client :)

    """   
    lastcall = 0
    
    def __init__(self, username, password, method='v1'):
        self.username, self.password = username, password
        self.method = method
        
    def __getattr__(self, method):
        return DeliciousClient(self.username, self.password, '%s/%s' % (self.method, method))
        
    def __repr__(self):
        return "<DeliciousClient: %s>" % self.method

    def __call__(self, **params):
        url = ("https://api.del.icio.us/%s?" % self.method) + urllib.urlencode(params)
        ctr = 0

        # HACK: try three times before giving up :/
        while True:
            try:
                # Enforce Yahoo's "no calls quicker than every 1 second" rule
                delta = time.time() - DeliciousClient.lastcall
                if delta < 2:
                    time.sleep(2 - delta)
                return utils.getxml(url, username=self.username, password=self.password)
            except Exception, e:
                if ctr+1 < 3:
                    log.debug("Fetching %s failed. Retrying" % url)
                    ctr += 1
                else:
                    raise e
            finally:
                DeliciousClient.lastcall = time.time()

class DeliciousProvider(StructuredDataProvider):
    """
    

    """
    class Meta:
        models   = (Bookmark,)
        settings = ('DELICIOUS_USERNAME','DELICIOUS_PASSWORD')

    def __init__(self):
        super(DeliciousProvider,self).__init__()
        self.register_custom_data_interface(DeliciousClient,Bookmark)

    def source_id(self, model_cls, extra):
        return extra['hash']

    def get_default_fields(self, model_cls):
        fields = super(DeliciousProvider,self).get_default_fields(model_cls)
        return [ field for field in fields if field.name != 'thumbnail' and field.name != 'thumbnail_url' ]

    def get_custom_data_interface_instance(self, interface_cls):
        return interface_cls(settings.DELICIOUS_USERNAME,settings.DELICIOUS_PASSWORD)

    def update_bookmark(self, delicious):
        last_update_date = Item.objects.get_last_update_of_model(Bookmark)
        bookmarks = self.incoming['bookmark'] = list()

        last_post_date = utils.parsedate(delicious.posts.update().get("time"))
        if last_post_date <= last_update_date:
            log.info("Skipping update: last update date: %s; last post date: %s", last_update_date, last_post_date)
            return

        for datenode in reversed(list(delicious.posts.dates().getiterator('date'))):
            dt = utils.parsedate(datenode.get("date"))
            if dt > last_update_date:
                xml = delicious.posts.get(dt=dt.strftime("%Y-%m-%d"))
                for post in xml.getiterator('post'):
                    info = dict((k, smart_unicode(post.get(k))) for k in post.keys())

                    info['tags'] = info['tag']
                    info['url'] = info['href']
                    info['timestamp'] = utils.parsedate(info['time'])

                    bookmarks.append( info )

register_provider( DeliciousProvider )
