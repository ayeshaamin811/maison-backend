from django.contrib import admin
from django.utils.html import format_html

from .forms import ProductAdminForm
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
    form = ProductAdminForm
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
        (
            'Product',
            {
                'fields': ['name', 'sku', 'collection', 'fabric', 'edits'],
                'description': (
                    'Collection is where the product lives (one only). '
                    'Edits are the extra menus it should also appear in - '
                    'tick as many as apply, or none.'
                ),
            },
        ),
        (
            'Pricing',
            {
                'fields': ['price', 'old_price', 'discount', 'reward_min', 'reward_max'],
                'description': (
                    'Plain numbers only - no "Rs." and no commas. The website '
                    'adds those. Leave old price and discount empty when the '
                    'product is not on sale.'
                ),
            },
        ),
        (
            'Images',
            {
                'fields': ['image', 'hover_image'],
                'description': (
                    'Image shows on the product card; hover image replaces it '
                    'when the mouse is over the card. Extra gallery shots go '
                    'at the bottom of this page.'
                ),
            },
        ),
        (
            'Description',
            {
                'fields': ['composition', 'shirt_detail', 'details', 'sizes'],
                'description': (
                    'Composition and Shirt detail are one short line each, '
                    'e.g. "2 Piece - Shirt &amp; Trouser" and "Printed Straight '
                    'Shirt".'
                ),
            },
        ),
        (
            'Availability',
            {'fields': ['stock', 'is_active', 'is_best_seller']},
        ),
    ]

    @admin.display(description='')
    def thumb(self, obj):
        if not obj.image:
            return '—'
        return format_html(
            '<img src="{}" style="height:56px;border-radius:4px" />', obj.image.url
        )
