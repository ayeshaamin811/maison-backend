from django.db import models


class Taxonomy(models.Model):
    """Shared shape for the three taxonomies the storefront filters on.

    `slug` is what appears in frontend URLs, so it is the stable identifier —
    renaming `name` is safe, renaming `slug` breaks live links.
    """

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name


class Collection(Taxonomy):
    """One per product — the 'By Collection' menu."""


class Fabric(Taxonomy):
    """Optional — not every product maps onto a listed fabric."""


class Edit(Taxonomy):
    """Many per product — the 'Main Menu' curated edits."""


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=80, unique=True)

    collection = models.ForeignKey(
        Collection, on_delete=models.PROTECT, related_name='products'
    )
    fabric = models.ForeignKey(
        Fabric,
        on_delete=models.SET_NULL,
        related_name='products',
        null=True,
        blank=True,
    )
    edits = models.ManyToManyField(Edit, related_name='products', blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Free text so the copy stays whatever merchandising wants ("25% OFF").
    discount = models.CharField(max_length=40, blank=True)

    reward_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    reward_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    image = models.ImageField(upload_to='products/')
    hover_image = models.ImageField(upload_to='products/', blank=True)

    composition = models.CharField(max_length=200, blank=True)
    shirt_detail = models.CharField(max_length=200, blank=True)
    details = models.JSONField(
        default=list, blank=True, help_text='List of strings, one per bullet.'
    )
    sizes = models.JSONField(
        default=list, blank=True, help_text='List of size labels, e.g. ["XS", "S"].'
    )

    stock = models.PositiveIntegerField(default=0)
    is_best_seller = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Catalogue order, matching how merchandising laid the grid out.
        # `?sort=newest` opts into recency.
        ordering = ['id']
        indexes = [
            models.Index(fields=['is_active', 'is_best_seller']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f'{self.name} ({self.sku})'


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='gallery'
    )
    image = models.ImageField(upload_to='products/')
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.product.sku} #{self.position}'
