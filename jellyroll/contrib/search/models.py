import urllib

from django.db import models
from jellyroll.core.models import Item


class SearchEngine(models.Model):
    """
    Simple encapsulation of a search engine.
    """
    name = models.CharField(max_length=200)
    home = models.URLField()
    search_template = models.URLField()

    class Meta:
        app_label = 'jellyroll'
    
    def __unicode__(self):
        return self.name
        
class WebSearch(models.Model):
    """
    A search made with a search engine. Modeled after Google's search history,
    but (may/could/will) work with other sources.
    """
    engine = models.ForeignKey(SearchEngine, related_name="searches")
    query = models.CharField(max_length=250)
    
    class Meta:
        verbose_name_plural = "web searches"
        app_label = 'jellyroll'

    def __unicode__(self):
        return self.query
        
    def url(self):
        return self.engine.search_template % (urllib.quote_plus(self.query))
    url = property(url)
        
class WebSearchResult(models.Model):
    """
    A page viewed as a result of a WebSearch
    """
    search = models.ForeignKey(WebSearch, related_name="results")
    title  = models.CharField(max_length=250)
    url    = models.URLField()

    class Meta:
        app_label = 'jellyroll'

    def __unicode__(self):
        return self.title

Item.objects.follow_model(WebSearch)
