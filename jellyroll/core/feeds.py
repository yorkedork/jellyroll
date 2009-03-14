from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed
from django.contrib.sites.models import Site

from jellyroll.core.models import Item


class JellyrollBaseFeed(Feed):

    item_class = Item

    def _get_verbose_name(self):
        return self.item_class._meta.verbose_name
    verbose_name = property(_get_verbose_name)

    def _get_verbose_name_plural(self):
        return self.item_class._meta.verbose_name_plural
    verbose_name_plural = property(_get_verbose_name_plural)

    def link(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return u"http://%s" % self._site.domain

    def item_link(self, item):
        return item.url

    def title(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return u"%s %s" % (self._site.name, self.verbose_name_plural)

    def description(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return u"Latest %s on %s" % (self._site.name, self.verbose_name_plural)

    def items(self):
        return Item.objects.get_for_model(self.item_class)

    def item_pubdate(self, item):
        return item.timestamp

class JellyrollBaseAtomFeed(JellyrollBaseFeed):
    feed_type = Atom1Feed
    subtitle = JellyrollBaseFeed.description

class JellyrollBaseRSSFeed(JellyrollBaseFeed):
    pass
