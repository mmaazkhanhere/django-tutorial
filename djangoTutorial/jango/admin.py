from django.contrib import admin
from .models import ChaiVariety, ChaiReviews, Store, ChaiCertificate

class ChaiReviewInLine(admin.TabularInline):
    model = ChaiReviews
    extra = 2 # you can see two fields to add Chai

class ChaiVarietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'date_added')
    inlines = [ChaiReviewInLine]

class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    filter_horizontal = ('chai_varieties',)

class ChaiCertificateAdmin(admin.ModelAdmin):
    list_display = ('chai', 'certificate_number')

# Register your models here.
admin.site.register(ChaiVariety, ChaiVarietyAdmin)
admin.site.register(Store, StoreAdmin)
admin.site.register(ChaiCertificate, ChaiCertificateAdmin)