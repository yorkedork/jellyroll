import django.forms
from django.contrib import admin
from jellyroll.contrib.photo.models import Photo, Photoset


class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'photo_id','description', 'taken_by')
    search_fields = ('title', 'description', 'taken_by')

class PhotosetAdmin(admin.ModelAdmin):
    list_display = ('title', 'photoset_id','description',)
    search_fields = ('title', 'description',)
    filter_horizontal = ('photos',)

admin.site.register(Photo, PhotoAdmin)
admin.site.register(Photoset, PhotosetAdmin)

