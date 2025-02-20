from django.contrib import admin
from .models import PCPContract, User, EmailTranscript


class PCPContractAdmin(admin.ModelAdmin):
    list_display = ('get_first_name', 'get_last_name', 'get_email', 'start_date', 'end_date')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    list_filter = ('start_date', 'end_date')

    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.admin_order_field = 'user__first_name'  # Allow sorting
    get_first_name.short_description = "First Name"

    def get_last_name(self, obj):
        return obj.user.last_name
    get_last_name.admin_order_field = 'user__last_name'
    get_last_name.short_description = "Last Name"

    def get_email(self, obj):
        return obj.user.email
    get_email.admin_order_field = 'user__email'
    get_email.short_description = "Email Address"


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'classification', 'is_contacted')
    search_fields = ('email',)
    list_filter = ('classification', 'is_contacted')


class EmailTranscriptAdmin(admin.ModelAdmin):
    list_display = ('customer_email', 'created_at', 'transcript')
    search_fields = ('customer_email',)
    list_filter = ('created_at',)


admin.site.register(User, UserAdmin)
admin.site.register(PCPContract, PCPContractAdmin)
admin.site.register(EmailTranscript, EmailTranscriptAdmin)
