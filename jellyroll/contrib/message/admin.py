import django.forms
from django.contrib import admin
from jellyroll.contrib.message.models import Message


class MessageAdmin(admin.ModelAdmin):
    list_display = ('message',)

admin.site.register(Message, MessageAdmin)
