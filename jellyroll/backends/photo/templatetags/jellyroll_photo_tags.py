from django.db import models
from django import template

# Hack until relative imports
#Photo = models.get_model("jellyroll", "photo")
Photoset = models.get_model("jellyroll", "photoset")


class PhotosetNode(template.Node):
    def __init__(self, name, context_var):
        self.name = name.strip('\"')
        self.context_var = context_var

    def render(self, context):
        try:
            photoset = Photoset.objects.get(title=self.name)
            context[self.context_var] = photoset.photos.all()
        except Photoset.DoesNotExist:
            pass

        return ''

def get_photoset(parser, token):
    bits = token.split_contents()

    if len(bits) != 4:
        raise template.TemplateSyntaxError("%r tag takes three arguments" % bits[0])
    elif bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to %r tag should be 'as'" % bits[0])
    return PhotosetNode(bits[1],bits[3])

register = template.Library()
get_photoset = register.tag(get_photoset)
