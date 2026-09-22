"""Contract tests for the products API.

The response shape is consumed by a storefront that parses `price` by hand, so
most of what is asserted here is formatting rather than logic: a drift in the
money format shows up as a wrong cart total, never as an error.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Collection, Edit, Fabric, Product, ProductImage

SPEC_KEYS = [
    'id', 'name', 'category', 'sku', 'price', 'priceValue', 'oldPrice',
    'discount', 'rewardMin', 'rewardMax', 'image', 'hoverImage', 'images',
    'composition', 'shirtDetail', 'details', 'sizes', 'stock', 'isBestSeller',
]


class SeedTests(TestCase):
    def test_taxonomy_slugs_seeded(self):
        self.assertEqual(
            sorted(Collection.objects.values_list('slug', flat=True)),
            ['casual', 'embroidered', 'formals', 'solids', 'unstitched', 'west'],
        )
        self.assertEqual(
            sorted(Fabric.objects.values_list('slug', flat=True)),
            ['crepe', 'lawn', 'linen', 'matte-twill', 'silk'],
        )
        self.assertEqual(
            sorted(Edit.objects.values_list('slug', flat=True)),
            ['co-ordsets', 'formal-edit', 'fusion-edit', 'new-arrivals'],
        )

    def test_all_26_products_seeded(self):
        self.assertEqual(Product.objects.count(), 26)
        self.assertEqual(Product.objects.filter(is_active=True).count(), 26)


class ResponseShapeTests(TestCase):
    def setUp(self):
        self.url = reverse('product-list')

    def test_keys_match_the_contract_exactly(self):
        row = self.client.get(self.url).json()['results'][0]
        self.assertEqual(list(row.keys()), SPEC_KEYS)

    def test_price_format(self):
        """`Rs.6,990.00` - no space, thousands separator, two decimals."""
        row = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertEqual(row['price'], 'Rs.6,990.00')
        self.assertEqual(row['priceValue'], 6990.00)

    def test_price_survives_the_frontend_parse(self):
        """Mirror what the storefront does: strip `Rs.` and commas, parseFloat."""
        for row in self.client.get(self.url + '?page_size=96').json()['results']:
            parsed = float(row['price'].replace('Rs.', '').replace(',', ''))
            self.assertEqual(
                Decimal(str(parsed)),
                Decimal(str(row['priceValue'])),
                'price string and priceValue disagree for {}'.format(row['sku']),
            )

    def test_reward_format_differs_from_price(self):
        """`Rs. 280` - space after Rs., no decimals, still comma-separated."""
        row = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertEqual(row['rewardMin'], 'Rs. 280')
        self.assertEqual(row['rewardMax'], 'Rs. 699')

        four_figure = self.client.get(reverse('product-detail', args=[19])).json()
        self.assertEqual(four_figure['rewardMax'], 'Rs. 1,299')

    def test_old_price_and_discount_are_null_when_absent(self):
        plain = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertIsNone(plain['oldPrice'])
        self.assertIsNone(plain['discount'])

        marked_down = self.client.get(reverse('product-detail', args=[7])).json()
        self.assertEqual(marked_down['oldPrice'], 'Rs.3,990.00')
        self.assertEqual(marked_down['discount'], '25% OFF')

    def test_category_is_collection_then_edits_then_fabric(self):
        row = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertEqual(row['category'], ['casual', 'new-arrivals', 'lawn'])

    def test_category_omits_fabric_when_unset(self):
        row = self.client.get(reverse('product-detail', args=[3])).json()
        self.assertEqual(row['category'], ['casual'])

    def test_image_urls_are_absolute(self):
        row = self.client.get(self.url).json()['results'][0]
        for url in [row['image'], row['hoverImage']] + row['images']:
            self.assertTrue(url.startswith('http://'), url)

    def test_images_falls_back_to_card_images(self):
        row = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertEqual(row['images'], [row['image'], row['hoverImage']])

    def test_images_uses_gallery_rows_when_present(self):
        product = Product.objects.get(pk=1)
        ProductImage.objects.create(
            product=product, image='products/image-2.webp', position=1
        )
        ProductImage.objects.create(
            product=product, image='products/image-3.webp', position=0
        )
        row = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertEqual(len(row['images']), 2)
        # Ordered by `position`, so image-3 (position 0) comes first.
        self.assertTrue(row['images'][0].endswith('image-3.webp'))
        self.assertTrue(row['images'][1].endswith('image-2.webp'))


class ListingTests(TestCase):
    def setUp(self):
        self.url = reverse('product-list')

    def test_pagination_is_24(self):
        body = self.client.get(self.url).json()
        self.assertEqual(body['count'], 26)
        self.assertEqual(len(body['results']), 24)
        self.assertIsNotNone(body['next'])
        self.assertIsNone(body['previous'])

        page_two = self.client.get(self.url + '?page=2').json()
        self.assertEqual(len(page_two['results']), 2)

    def test_inactive_products_are_hidden(self):
        Product.objects.filter(pk=1).update(is_active=False)
        body = self.client.get(self.url).json()
        self.assertEqual(body['count'], 25)
        self.assertNotIn(1, [row['id'] for row in body['results']])
        self.assertEqual(
            self.client.get(reverse('product-detail', args=[1])).status_code, 404
        )

    def _ids(self, query=''):
        body = self.client.get(self.url + '?page_size=96&' + query).json()
        return [row['id'] for row in body['results']]

    def test_single_filters(self):
        self.assertEqual(self._ids('collection=casual'), [1, 2, 3, 4, 5])
        self.assertEqual(self._ids('edit=new-arrivals'), [1, 7, 23])
        self.assertEqual(self._ids('is_best_seller=true'), [23, 24])
        self.assertEqual(self._ids('fabric=linen'), [15])
        self.assertEqual(self._ids('size=Unstitched'), [11, 12, 13, 14])

    def test_size_token_is_exact(self):
        """`S` must not match `XS` - the JSON is matched on the quoted token."""
        self.assertNotIn(11, self._ids('size=S'))
        self.assertEqual(len(self._ids('size=S')), 22)
        self.assertEqual(len(self._ids('size=M')), 22)

    def test_price_bounds(self):
        ids = self._ids('min_price=6000&max_price=9000')
        prices = Product.objects.filter(pk__in=ids).values_list('price', flat=True)
        self.assertTrue(all(Decimal(6000) <= p <= Decimal(9000) for p in prices))
        self.assertEqual(ids, [1, 2, 15, 17, 23, 24])

    def test_search_spans_name_and_sku(self):
        self.assertEqual(self._ids('search=velvet'), [22, 26])
        self.assertEqual(self._ids('search=EMB-02'), [24])

    def test_filters_combine(self):
        self.assertEqual(
            self._ids(
                'collection=casual&edit=formal-edit&size=XL'
                '&min_price=1000&max_price=5000&sort=price-desc'
            ),
            [4],
        )

    def _prices(self, query):
        ids = self._ids(query)
        by_id = Product.objects.in_bulk(ids)
        return [by_id[pk].price for pk in ids]

    def test_sorting(self):
        ascending = self._prices('sort=price-asc')
        self.assertEqual(ascending, sorted(ascending))
        descending = self._prices('sort=price-desc')
        self.assertEqual(descending, sorted(descending, reverse=True))

        self.assertEqual(self._ids('sort=price-asc')[0], 7)  # Rs.2,993.00
        self.assertEqual(self._ids('sort=price-desc')[0], 22)  # Rs.18,990.00

        # Ties break on id ascending in both directions, so the two orderings
        # are not mirror images of one another - that stability is deliberate.
        self.assertEqual(self._ids('sort=price-asc')[:3], [7, 8, 10])

    def test_best_sellers_sort_floats_them_up(self):
        self.assertEqual(self._ids('sort=best-sellers')[:2], [23, 24])

    def test_default_order_is_catalogue_order(self):
        self.assertEqual(self._ids(), list(range(1, 27)))

    def test_unknown_values_give_empty_200_never_404(self):
        for query in [
            'collection=does-not-exist',
            'fabric=nope',
            'edit=nope',
            'size=XXXL',
            'collection=casual&fabric=silk',
        ]:
            response = self.client.get(self.url + '?' + query)
            self.assertEqual(response.status_code, 200, query)
            self.assertEqual(response.json()['count'], 0, query)

    def test_malformed_params_are_ignored_not_rejected(self):
        for query in ['sort=banana', 'min_price=abc', 'max_price=xyz', 'page_size=0']:
            response = self.client.get(self.url + '?' + query)
            self.assertEqual(response.status_code, 200, query)
            self.assertEqual(response.json()['count'], 26, query)


class AdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('staff', 'staff@example.com', 'pw')
        self.client.force_login(User.objects.get(username='staff'))

    def test_product_pages_render(self):
        for url in [
            '/admin/products/product/',
            '/admin/products/product/add/',
            '/admin/products/product/1/change/',
            '/admin/products/collection/',
            '/admin/products/fabric/',
            '/admin/products/edit/',
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_a_product_can_be_created_without_code(self):
        collection = Collection.objects.get(slug='casual')
        edit = Edit.objects.get(slug='new-arrivals')
        with open('media/products/image-1.webp', 'rb') as handle:
            artwork = SimpleUploadedFile(
                'admin-upload.webp', handle.read(), content_type='image/webp'
            )
        response = self.client.post(
            '/admin/products/product/add/',
            {
                'image': artwork,
                'name': 'Admin Created Suit',
                'sku': 'ADM-01',
                'is_active': 'on',
                'stock': '4',
                'collection': collection.pk,
                'fabric': '',
                'edits': [edit.pk],
                'price': '1234.50',
                'old_price': '',
                'discount': '',
                'reward_min': '50',
                'reward_max': '123',
                'composition': '1 Piece - Shirt',
                'shirt_detail': 'Test Shirt',
                'details': '["Fabric: Lawn"]',
                'sizes': '["S", "M"]',
                'gallery-TOTAL_FORMS': '0',
                'gallery-INITIAL_FORMS': '0',
                'gallery-MIN_NUM_FORMS': '0',
                'gallery-MAX_NUM_FORMS': '1000',
            },
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])

        created = Product.objects.get(sku='ADM-01')
        row = self.client.get(reverse('product-detail', args=[created.pk])).json()
        self.assertEqual(row['price'], 'Rs.1,234.50')
        self.assertEqual(row['rewardMin'], 'Rs. 50')
        self.assertEqual(row['category'], ['casual', 'new-arrivals'])
        self.assertIsNone(row['oldPrice'])
        self.assertIsNone(row['discount'])


class StorageTests(TestCase):
    """The API must hand out fetchable URLs under either storage backend."""

    R2 = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                'bucket_name': 'maison-media',
                'endpoint_url': 'https://acct123.r2.cloudflarestorage.com',
                'access_key': 'test-key',
                'secret_key': 'test-secret',
                'region_name': 'auto',
                'addressing_style': 'path',
                'default_acl': None,
                'querystring_auth': False,
                'custom_domain': 'cdn.example.com',
            },
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'
        },
    }

    def test_local_storage_urls_are_absolute(self):
        row = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertEqual(
            row['image'], 'http://testserver/media/products/image-1.webp'
        )

    def test_r2_urls_use_the_public_domain_and_are_unsigned(self):
        with self.settings(STORAGES=self.R2):
            row = self.client.get(reverse('product-detail', args=[1])).json()

        self.assertEqual(
            row['image'], 'https://cdn.example.com/products/image-1.webp'
        )
        self.assertEqual(
            row['hoverImage'],
            'https://cdn.example.com/products/image-1-hover.webp',
        )
        self.assertEqual(row['images'], [row['image'], row['hoverImage']])
        # No presigned querystring - these are public catalogue assets and a
        # signed URL would expire behind the storefront's CDN cache.
        self.assertNotIn('?', row['image'])
        self.assertNotIn('X-Amz-Signature', row['image'])

    def test_r2_urls_do_not_get_the_request_host_prepended(self):
        with self.settings(STORAGES=self.R2):
            row = self.client.get(reverse('product-detail', args=[1])).json()
        self.assertNotIn('testserver', row['image'])


class CategoryParamTests(TestCase):
    """`?category=` mirrors the storefront's `category.includes(slug)`."""

    def _ids(self, query):
        url = reverse('product-list') + '?page_size=96&' + query
        return [row['id'] for row in self.client.get(url).json()['results']]

    def test_matches_a_collection_slug(self):
        self.assertEqual(self._ids('category=casual'), [1, 2, 3, 4, 5])

    def test_matches_an_edit_slug(self):
        self.assertEqual(self._ids('category=new-arrivals'), [1, 7, 23])

    def test_matches_a_fabric_slug(self):
        self.assertEqual(self._ids('category=linen'), [15])

    def test_agrees_with_the_serialised_category_array(self):
        """Whatever a product lists in `category` must find it again."""
        listing = self.client.get(
            reverse('product-list') + '?page_size=96'
        ).json()['results']
        for row in listing:
            for slug in row['category']:
                self.assertIn(
                    row['id'],
                    self._ids('category=' + slug),
                    '{} lists "{}" but ?category={} misses it'.format(
                        row['sku'], slug, slug
                    ),
                )

    def test_repeating_it_narrows(self):
        self.assertEqual(self._ids('category=casual&category=new-arrivals'), [1])

    def test_unknown_slug_is_empty_not_404(self):
        response = self.client.get(reverse('product-list') + '?category=nope')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 0)
