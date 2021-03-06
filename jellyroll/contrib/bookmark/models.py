from django.db import models
from jellyroll.core.models import Item


class Bookmark(models.Model):
    """
    A bookmarked link. The model is based on del.icio.us, with the added
    thumbnail field for ma.gnolia users.
    """
    
    url           = models.URLField(unique=True, max_length=1000)
    description   = models.CharField(max_length=255)
    extended      = models.TextField(blank=True)
    thumbnail     = models.ImageField(upload_to="img/jellyroll/bookmarks/%Y/%m", blank=True)
    thumbnail_url = models.URLField(blank=True, verify_exists=False, max_length=1000)

    class Meta:
        app_label = 'jellyroll'

    def __unicode__(self):
        return self.url

Item.objects.follow_model(Bookmark)
