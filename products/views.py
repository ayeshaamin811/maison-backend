from rest_framework import generics

from .filters import apply_filters
from .models import Product
from .pagination import ProductPagination
from .serializers import ProductSerializer


class ProductQuerysetMixin:
    serializer_class = ProductSerializer

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related('collection', 'fabric')
            .prefetch_related('edits', 'gallery')
        )


class ProductListView(ProductQuerysetMixin, generics.ListAPIView):
    pagination_class = ProductPagination

    def get_queryset(self):
        return apply_filters(super().get_queryset(), self.request.query_params)


class ProductDetailView(ProductQuerysetMixin, generics.RetrieveAPIView):
    pass
