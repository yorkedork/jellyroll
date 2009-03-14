import django.forms

from django.contrib import admin
from jellyroll.contrib.video.models import Video


class VideoAdmin(admin.ModelAdmin):
    list_display = ('title',)

admin.site.register(Video, VideoAdmin)
