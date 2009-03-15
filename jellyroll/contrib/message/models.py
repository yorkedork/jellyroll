import md5

from django.db import models
from django.utils import text

from jellyroll.core.models import Item
from jellyroll.contrib.utils.models import ContentLink


class Message(models.Model):
    """
    A message, status update, or "tweet".

    """
    message = models.TextField()
    links = models.ManyToManyField(ContentLink,blank=True,null=True)

    class Meta:
        app_label = 'jellyroll'

    def __unicode__(self):
        return text.truncate_words(self.message, 30)

Item.objects.follow_model(Message)
