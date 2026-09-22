"""Query-param filtering for the product list.

Deliberately forgiving: an unknown slug, a malformed price or an unrecognised
sort key narrows or is ignored rather than raising. The storefront builds these
params from user-editable URLs, so a 404/400 there is a worse experience than
an empty grid.
"""
from decimal import Decimal, InvalidOperation

from django.db.models import Q, TextField
from django.db.models.functions import Cast

TRUTHY = {'1', 'true', 'yes', 'on'}
FALSY = {'0', 'false', 'no', 'off'}

SORTS = {
    'default': ['id'],
    'newest': ['-created_at', '-id'],
    'oldest': ['created_at', 'id'],
    'price-asc': ['price', 'id'],
    'price-desc': ['-price', 'id'],
    'name-asc': ['name', 'id'],
    'name-desc': ['-name', 'id'],
    'best-sellers': ['-is_best_seller', 'id'],
}
DEFAULT_SORT = SORTS['default']


def _values(params, key):
    """Collect a param given either repeated (`?edit=a&edit=b`) or comma-joined."""
    out = []
    for raw in params.getlist(key):
        out += [part.strip() for part in raw.split(',') if part.strip()]
    return out


def _decimal(raw):
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _by_size(queryset, sizes):
    """Match products whose `sizes` JSON list holds any of the given labels.

    JSONField's `contains` lookup is unsupported on SQLite, so this casts the
    column to text and matches the quoted token instead. The quotes make it
    exact: `"S"` cannot match inside `"XS"`, because the character before the
    S there is an X rather than the opening quote.
    """
    queryset = queryset.annotate(sizes_text=Cast('sizes', TextField()))
    clause = Q()
    for size in sizes:
        clause |= Q(sizes_text__contains='"{}"'.format(size))
    return queryset.filter(clause)


def apply_filters(queryset, params):
    for key, lookup in (
        ('collection', 'collection__slug__in'),
        ('fabric', 'fabric__slug__in'),
    ):
        slugs = _values(params, key)
        if slugs:
            queryset = queryset.filter(**{lookup: slugs})

    # Each `edit` narrows further, so ?edit=a&edit=b means "in both".
    for slug in _values(params, 'edit'):
        queryset = queryset.filter(edits__slug=slug)

    # `category` is the server-side twin of the storefront's
    # `product.category.includes(slug)`: it matches a collection, an edit or a
    # fabric without the caller having to know which kind the slug is. Routes
    # like /collection/<slug> use it; a filter sidebar wants the precise
    # `collection` / `edit` / `fabric` params above instead.
    for slug in _values(params, 'category'):
        queryset = queryset.filter(
            Q(collection__slug=slug) | Q(edits__slug=slug) | Q(fabric__slug=slug)
        )

    best_seller = params.get('is_best_seller', '').strip().lower()
    if best_seller in TRUTHY:
        queryset = queryset.filter(is_best_seller=True)
    elif best_seller in FALSY:
        queryset = queryset.filter(is_best_seller=False)

    sizes = _values(params, 'size')
    if sizes:
        queryset = _by_size(queryset, sizes)

    minimum = _decimal(params.get('min_price'))
    if minimum is not None:
        queryset = queryset.filter(price__gte=minimum)

    maximum = _decimal(params.get('max_price'))
    if maximum is not None:
        queryset = queryset.filter(price__lte=maximum)

    search = params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(shirt_detail__icontains=search)
            | Q(composition__icontains=search)
            | Q(collection__name__icontains=search)
        )

    ordering = SORTS.get(params.get('sort', '').strip().lower(), DEFAULT_SORT)
    # An `edit` filter joins through the M2M and can fan a product across rows.
    return queryset.order_by(*ordering).distinct()
