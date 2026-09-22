from rest_framework import serializers

from .models import Product


def money(value):
    """Product/cart price format: `Rs.6,990.00`.

    The frontend strips `Rs.` and commas then parseFloat()s the rest, so the
    two decimals and the thousands separator are load-bearing — a drift here
    shows up as a wrong cart total, not as an error.
    """
    if value is None:
        return None
    return f'Rs.{value:,.2f}'


def reward(value):
    """Reward-points format: `Rs. 280` — space after `Rs.`, no decimals."""
    if value is None:
        return None
    return f'Rs. {value:,.0f}'


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    priceValue = serializers.DecimalField(
        source='price', max_digits=10, decimal_places=2, coerce_to_string=False
    )
    oldPrice = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    rewardMin = serializers.SerializerMethodField()
    rewardMax = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    hoverImage = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    shirtDetail = serializers.CharField(source='shirt_detail')
    isBestSeller = serializers.BooleanField(source='is_best_seller')

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'category',
            'sku',
            'price',
            'priceValue',
            'oldPrice',
            'discount',
            'rewardMin',
            'rewardMax',
            'image',
            'hoverImage',
            'images',
            'composition',
            'shirtDetail',
            'details',
            'sizes',
            'stock',
            'isBestSeller',
        ]

    def _absolute(self, image):
        """Absolute URLs so the storefront can render straight from any origin.

        R2 (and any CDN-backed storage) already hands back a fully qualified
        URL on its own domain, so only local media needs the request's scheme
        and host prepended.
        """
        if not image:
            return None
        url = image.url
        if url.startswith(('http://', 'https://')):
            return url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_category(self, obj):
        """Flat array: collection slug, then edit slugs, then fabric slug."""
        slugs = [obj.collection.slug]
        slugs += [edit.slug for edit in obj.edits.all()]
        if obj.fabric_id:
            slugs.append(obj.fabric.slug)
        return slugs

    def get_price(self, obj):
        return money(obj.price)

    def get_oldPrice(self, obj):
        return money(obj.old_price)

    def get_discount(self, obj):
        # Absent means null, never "" or 0.
        return obj.discount or None

    def get_rewardMin(self, obj):
        return reward(obj.reward_min)

    def get_rewardMax(self, obj):
        return reward(obj.reward_max)

    def get_image(self, obj):
        return self._absolute(obj.image)

    def get_hoverImage(self, obj):
        return self._absolute(obj.hover_image)

    def get_images(self, obj):
        gallery = [self._absolute(row.image) for row in obj.gallery.all()]
        if gallery:
            return [url for url in gallery if url]
        # No gallery rows — fall back to the two card images.
        return [url for url in (self.get_image(obj), self.get_hoverImage(obj)) if url]
