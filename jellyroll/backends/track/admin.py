import django.forms
from django.contrib import admin
from jellyroll.backends.track.models import Track


class TrackAdmin(admin.ModelAdmin):
    list_display = ('track_name', 'artist_name')
    search_fields = ("artist_name", "track_name")

admin.site.register(Track, TrackAdmin)
