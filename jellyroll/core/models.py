import urllib
import urlparse

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from django.utils import simplejson, text
from django.utils.encoding import smart_unicode

from jellyroll.core.managers import ItemManager
from tagging.fields import TagField


class Item(models.Model):
    """
    A generic jellyroll item. Slightly denormalized for performance.
    """

    # Generic relation to the object.
    content_type = models.ForeignKey(ContentType)
    object_id = models.TextField()
    object = generic.GenericForeignKey('content_type', 'object_id')
    
    # "Standard" metadata each object provides.
    url = models.URLField(blank=True, max_length=1000)
    timestamp = models.DateTimeField()
    tags = TagField(max_length=2500)
    
    # Metadata about where the object "came from" -- used by data providers to
    # figure out which objects to update when asked.
    source = models.CharField(max_length=100, blank=True)
    source_id = models.TextField(blank=True)
    
    # Denormalized object __unicode__, for performance 
    object_str = models.TextField(blank=True)
    
    objects = ItemManager()
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = [("content_type", "object_id")]
        app_label = "jellyroll"
    
    def __unicode__(self):
        return "%s: %s" % (self.content_type.model_class().__name__, self.object_str)
        
    def __cmp__(self, other):
        return cmp(self.timestamp, other.timestamp)
    
    def save(self, force_insert=False, force_update=False):
        ct = "%s_%s" % (self.content_type.app_label, self.content_type.model.lower())
        self.object_str = smart_unicode(self.object)
        super(Item, self).save(force_insert, force_update)
