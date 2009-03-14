from django.contrib.contenttypes.models import ContentType
from django.db import models
from django import template

# Hack until relative imports
CodeRepository = models.get_model("jellyroll", "coderepository")
CodeCommit = models.get_model("jellyroll", "codecommit")
Item = models.get_model("jellyroll", "item")


class CodeCommitsForRepositoryNode(template.Node):
    def __init__(self, repository_name, context_var, limit=None):
        self.repository_name = repository_name.strip("\"")
        self.context_var = context_var
        self.limit = limit

    def render(self, context):
        try:
            repository = CodeRepository.objects.get(name=self.repository_name)
            ct = ContentType.objects.get_for_model(CodeCommit)
            codecommit_items = Item.objects.filter(content_type=ct).order_by("-timestamp")
            codecommits = [ item.object for item in codecommit_items if item.object.repository == repository ]
            if self.limit:
                context[self.context_var] = codecommits[:self.limit]
            else:
                context[self.context_var] = codecommits
        except CodeRepository.DoesNotExist:
            pass

        return ''

def get_commits_for_repository(parser, token):
    bits = token.split_contents()

    if len(bits) != 4 and len(bits) != 6:
        raise template.TemplateSyntaxError("%r tag takes three or five arguments" % bits[0])
    elif bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to %r tag should be 'as'" % bits[0])
    elif len(bits) == 6 and bits[4] != 'limit':
        raise template.TemplateSyntaxError("fourth argument to %r tag should be 'limit'" % bits[0])

    limit = None
    if len(bits) == 6:
        limit = int(bits[5])
    return CodeCommitsForRepositoryNode(bits[1],bits[3],limit)

register = template.Library()
get_commits_for_repository = register.tag(get_commits_for_repository)
