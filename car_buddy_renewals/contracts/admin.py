from django.contrib import admin
from .models import PCPContract, User, EmailTranscript
# Register your models here.

class PCPContractAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email_address', 'start_date', 'end_date')
    search_fields = ('first_name', 'last_name', 'email_address')
    list_filter = ('start_date', 'end_date')

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'classification', 'is_contacted')
    search_fields = ('email',)
    list_filter = ('classification', 'is_contacted')

class EmailTranscriptAdmin(admin.ModelAdmin):
    list_display = ('customer_email', 'created_at', 'transcript')
    search_fields = ('customer_email',)
    list_filter = ('created_at',)



admin.site.register(User)
admin.site.register(PCPContract)
admin.site.register(EmailTranscript)