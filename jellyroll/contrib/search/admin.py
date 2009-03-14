import django.forms
from django.contrib import admin
from jellyroll.contrib.search.models import WebSearch, WebSearchResult


class WebSearchResultInline(admin.TabularInline):
    model = WebSearchResult

class WebSearchAdmin(admin.ModelAdmin):
    list_display = ('query',)
    inlines = [WebSearchResultInline]

admin.site.register(WebSearch, WebSearchAdmin)

