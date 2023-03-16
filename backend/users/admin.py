from django.contrib import admin

from .models import Subscribtion, User


class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'password',
                    'email', 'first_name', 'last_name')
    search_fields = ('username',)
    list_filter = ('email', 'username',)
    empty_value_display = '-empty-'


admin.site.register(User, UserAdmin)
admin.site.register(Subscribtion)
