import django.forms
from django.contrib import admin
from jellyroll.contrib.code.models import CodeCommit, CodeRepository


class CodeRepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'url')
    prepopulated_fields = {"slug": ("name",)}

    class CodeRepositoryForm(django.forms.ModelForm):
        class Meta:
            model = CodeRepository
            
        # Override the URL field to be more permissive
        url = django.forms.CharField(required=True, max_length=100)
        
    form = CodeRepositoryForm

class CodeCommitAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'repository')
    list_filter = ('repository',)
    search_fields = ('message',)

admin.site.register(CodeRepository, CodeRepositoryAdmin)
admin.site.register(CodeCommit, CodeCommitAdmin)
