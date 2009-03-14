from django.db import models


class ContentLink(models.Model):
    """
    A non-resource reference to be associated with
    a model. 

    In other words, not the canonical location
    for a resource defined by a jellyroll model, but 
    instead a topical resource given in the resource 
    body itself in a format that varies across model
    type.

    """
    url = models.URLField()
    identifier = models.CharField(max_length=128)

    class Meta:
        app_label = 'jellyroll'

    def __unicode__(self):
        return self.identifier
