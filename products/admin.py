from django.contrib import admin
from django.utils.html import format_html

from .models import Collection, Edit, Fabric, Product, ProductImage


class TaxonomyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Products')
    def product_count(self, obj):
        return obj.products.count()


admin.site.register(Collection, TaxonomyAdmin)
admin.site.register(Fabric, TaxonomyAdmin)
admin.site.register(Edit, TaxonomyAdmin)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'preview', 'position']
    readonly_fields = ['preview']

    @admin.display(description='Preview')
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return '—'
        return format_html(
            '<img src="{}" style="height:80px;border-radius:4px" />', obj.image.url
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'thumb',
        'name',
        'sku',
        'collection',
        'fabric',
        'price',
        'stock',
        'is_best_seller',
        'is_active',
    ]
    list_display_links = ['thumb', 'name']
    list_filter = ['collection', 'fabric', 'edits', 'is_best_seller', 'is_active']
    list_editable = ['stock', 'is_best_seller', 'is_active']
    search_fields = ['name', 'sku', 'shirt_detail', 'composition']
    filter_horizontal = ['edits']
    inlines = [ProductImageInline]
    date_hierarchy = 'created_at'
    save_on_top = True

    fieldsets = [
        (None, {'fields': ['name', 'sku', 'is_active', 'is_best_seller', 'stock']}),
        ('Categorisation', {'fields': ['collection', 'fabric', 'edits']}),
        (
            'Pricing',
            {
                'fields': ['price', 'old_price', 'discount', 'reward_min', 'reward_max'],
                'description': (
                    'Enter plain numbers — the API formats them as '
                    '<code>Rs.6,990.00</code> and <code>Rs. 280</code>. '
                    'Leave old price / discount empty when there is no markdown.'
                ),
            },
        ),
        ('Card images', {'fields': ['image', 'hover_image']}),
        (
            'Description',
            {
                'fields': ['composition', 'shirt_detail', 'details', 'sizes'],
                'description': (
                    'Details and sizes are JSON lists, e.g. '
                    '<code>["Fabric: Lawn", "Wash Care: Dry clean only"]</code> '
                    'and <code>["XS", "S", "M", "L", "XL"]</code>.'
                ),
            },
        ),
    ]

    @admin.display(description='')
    def thumb(self, obj):
        if not obj.image:
            return '—'
        return format_html(
            '<img src="{}" style="height:56px;border-radius:4px" />', obj.image.url
        )
