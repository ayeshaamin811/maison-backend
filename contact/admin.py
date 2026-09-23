from django.contrib import admin, messages

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'created_at', 'is_read']
    list_display_links = ['first_name', 'last_name', 'email']
    list_filter = ['is_read', 'created_at']
    list_editable = ['is_read']
    search_fields = ['email', 'message']
    readonly_fields = ['first_name', 'last_name', 'email', 'message', 'created_at']
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread']

    fieldsets = [
        (None, {'fields': ['first_name', 'last_name', 'email', 'created_at']}),
        ('Message', {'fields': ['message']}),
        ('Status', {'fields': ['is_read']}),
    ]

    def has_add_permission(self, request):
        # These arrive from the storefront form; typing one by hand would only
        # ever be a mistake.
        return False

    @admin.action(description='Mark selected messages as read')
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(
            request,
            '{} message(s) marked as read.'.format(updated),
            messages.SUCCESS,
        )

    @admin.action(description='Mark selected messages as unread')
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(
            request,
            '{} message(s) marked as unread.'.format(updated),
            messages.SUCCESS,
        )
