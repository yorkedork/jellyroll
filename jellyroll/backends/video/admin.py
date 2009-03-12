import django.forms

from django.contrib import admin
from jellyroll.backends.video.models import Video


class VideoAdmin(admin.ModelAdmin):
    list_display = ('title',)

admin.site.register(Video, VideoAdmin)
