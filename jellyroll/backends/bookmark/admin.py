import django.forms
from django.contrib import admin
from jellyroll.backends.bookmark.models import Bookmark


class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('url', 'description')
    search_fields = ('url', 'description', 'thumbnail')

admin.site.register(Bookmark, BookmarkAdmin)
