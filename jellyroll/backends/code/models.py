from django.utils import text
from django.db import models
from jellyroll.backends.item.models import Item


SCM_CHOICES = (
    ("svn", "Subversion"),
    ("git", "Git"),
)

class CodeRepository(models.Model):
    """
    A code repository that you check code into somewhere. Currently only SVN
    is supported, but other forms should be hard to support.
    """
    type = models.CharField(max_length=10, choices=SCM_CHOICES)
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    username = models.CharField(max_length=100, help_text="Your username/email for this SCM.")
    public_changeset_template = models.URLField(
        verify_exists = False, blank = True,
        help_text = "Template for viewing a changeset publically. Use '%s' for the revision number")
    url = models.URLField()

    class Meta:
        verbose_name_plural = "code repositories"
        app_label = 'jellyroll'

    def __unicode__(self):
        return self.name

class CodeCommit(models.Model):
    """
    A code change you checked in.
    """
    repository = models.ForeignKey(CodeRepository, related_name="commits")
    revision = models.CharField(max_length=200)
    message = models.TextField()

    class Meta:
        ordering = ["-revision"]
        app_label = 'jellyroll'

    def __unicode__(self):
        return "[%s] %s" % (self.format_revision(), text.truncate_words(self.message, 10))

    def format_revision(self):
        """
        Shorten hashed revisions for nice reading.
        """
        try:
            return str(int(self.revision))
        except ValueError:
            return self.revision[:7]

    def url(self):
        if self.repository.public_changeset_template:
            return self.repository.public_changeset_template % self.revision
        return ""
    url = property(url)

Item.objects.follow_model(CodeCommit)
