"""Port the 26 storefront products from the frontend's src/data/products.jsx.

Columns, in order:
    name, sku, collection, fabric, edits, price, old_price, discount,
    reward_min, reward_max, image number, composition, shirt detail,
    fabric label, wash care, sizes, stock, is_best_seller

`fabric` is the FK slug and is not always set. The frontend's fabric labels are
free text ("Crosshatch", "Organza", "Karandi") and only some of them land on one
of the five filterable fabrics; the rest stay null rather than being forced into
a bucket that would make the fabric filter lie.
"""
import datetime
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import migrations
from django.utils import timezone

# The eight card images ship in the repo so a fresh clone seeds a working
# catalogue; MEDIA_ROOT itself is gitignored because it also collects
# merchandiser uploads.
SEED_ASSETS = Path(__file__).resolve().parent.parent / 'seed_assets'

STD = ['XS', 'S', 'M', 'L', 'XL']
UNS = ['Unstitched']
ORIGIN = 'Country of Origin: Pakistan'

PRODUCTS = [
    ('2 Pc Printed Cambric Suit', 'MB-MN26-08-BLACK-EX LARGE', 'casual', 'lawn', ['new-arrivals'], '6990.00', None, '', 280, 699, 1, '2 Piece - Shirt & Trouser', 'Printed Straight Shirt', 'Cambric', 'Dry clean only', STD, 2, False),
    ('2 PC Embroidered Slub Lawn Suit', 'MB-MN26-09-BLUE-M', 'casual', 'lawn', [], '7290.00', None, '', 290, 729, 2, '2 Piece - Shirt & Trouser', 'Embroidered Slub Lawn Shirt', 'Slub Lawn', 'Machine wash cold', STD, 5, False),
    ('2 PC Dyed Crosshatch Suit', 'MB-MN26-10-GREY-L', 'casual', None, [], '5990.00', None, '', 240, 599, 3, '2 Piece - Shirt & Trouser', 'Dyed Crosshatch Shirt', 'Crosshatch', 'Dry clean only', STD, 8, False),
    ('Printed Lawn Shirt', 'MB-MN26-11-WHITE-S', 'casual', 'lawn', ['formal-edit'], '4290.00', None, '', 170, 429, 4, '1 Piece - Shirt', 'Printed Lawn Shirt', 'Lawn', 'Machine wash cold', STD, 3, False),
    ('Printed Lawn Shirt', 'MB-MN26-12-WHITE-M', 'casual', 'lawn', [], '4290.00', None, '', 170, 429, 4, '1 Piece - Shirt', 'Printed Lawn Shirt', 'Lawn', 'Machine wash cold', STD, 3, False),

    ('2 PC Dyed Crosshatch Suit', 'SLD-01-BLACK-M', 'solids', None, [], '5990.00', None, '', 240, 599, 1, '2 Piece - Shirt & Trouser', 'Dyed Crosshatch Shirt', 'Crosshatch', 'Dry clean only', STD, 6, False),
    ('Dyed Dobby Cotton Shirt', 'SLD-02-BLUE-M', 'solids', None, ['new-arrivals'], '2993.00', '3990.00', '25% OFF', 120, 299, 2, '1 Piece - Shirt', 'Dyed Dobby Cotton Shirt', 'Dobby Cotton', 'Machine wash cold', STD, 7, False),
    ('Dyed Crosshatch Shirt', 'SLD-03-GREY-M', 'solids', None, [], '2993.00', '3990.00', '25% OFF', 120, 299, 3, '1 Piece - Shirt', 'Dyed Crosshatch Shirt', 'Crosshatch', 'Dry clean only', STD, 4, False),
    ('2 PC Dyed Arabic Lawn Suit', 'SLD-04-GREEN-M', 'solids', 'lawn', [], '4493.00', '5990.00', '25% OFF', 180, 449, 4, '2 Piece - Shirt & Trouser', 'Dyed Arabic Lawn Shirt', 'Arabic Lawn', 'Machine wash cold', STD, 9, False),
    ('Dyed Crosshatch Shirt', 'SLD-05-GREY-L', 'solids', None, [], '2993.00', '3990.00', '25% OFF', 120, 299, 3, '1 Piece - Shirt', 'Dyed Crosshatch Shirt', 'Crosshatch', 'Dry clean only', STD, 5, False),

    ('Printed Lawn Unstitched Suit', 'UNS-01-WHITE-M', 'unstitched', 'lawn', [], '3490.00', None, '', 140, 349, 1, '3 Piece - Shirt, Trouser & Dupatta', 'Printed Lawn Unstitched Shirt', 'Lawn', 'Hand wash recommended', UNS, 10, False),
    ('Embroidered Cotton Unstitched Suit', 'UNS-02-PINK-M', 'unstitched', None, ['co-ordsets'], '4990.00', '5990.00', '17% OFF', 199, 499, 2, '3 Piece - Shirt, Trouser & Dupatta', 'Embroidered Cotton Unstitched Shirt', 'Cotton', 'Hand wash recommended', UNS, 6, False),
    ('Dyed Karandi Unstitched Suit', 'UNS-03-GREY-M', 'unstitched', None, [], '5290.00', None, '', 210, 529, 3, '2 Piece - Shirt & Trouser', 'Dyed Karandi Unstitched Shirt', 'Karandi', 'Dry clean only', UNS, 4, False),
    ('Printed Cambric Unstitched Suit', 'UNS-04-BLUE-M', 'unstitched', 'lawn', [], '3990.00', None, '', 159, 399, 4, '2 Piece - Shirt & Trouser', 'Printed Cambric Unstitched Shirt', 'Cambric', 'Hand wash recommended', UNS, 8, False),

    ('Co-ord Linen West Set', 'WST-01-BEIGE-M', 'west', 'linen', ['co-ordsets'], '6490.00', None, '', 259, 649, 1, '2 Piece - Top & Trouser', 'Linen Co-ord Top', 'Linen', 'Machine wash cold', STD, 5, False),
    ('Wide Leg Trouser Co-ord', 'WST-02-BLACK-M', 'west', 'crepe', ['co-ordsets'], '5990.00', '6990.00', '14% OFF', 240, 599, 2, '2 Piece - Shirt & Wide Leg Trouser', 'Relaxed Fit Shirt', 'Crepe', 'Dry clean only', STD, 7, False),
    ('Structured Blazer Set', 'WST-03-GREY-M', 'west', None, [], '8290.00', None, '', 330, 829, 3, '2 Piece - Blazer & Trouser', 'Structured Blazer', 'Suiting Fabric', 'Dry clean only', STD, 3, False),
    ('Casual Jumpsuit', 'WST-04-OLIVE-M', 'west', None, [], '4790.00', None, '', 191, 479, 4, '1 Piece - Jumpsuit', 'Relaxed Fit Jumpsuit', 'Viscose', 'Machine wash cold', STD, 6, False),

    ('Embellished Formal Suit', 'FRM-01-MAROON-M', 'formals', None, ['formal-edit'], '12990.00', None, '', 519, 1299, 1, '3 Piece - Shirt, Trouser & Dupatta', 'Embellished Formal Shirt', 'Organza', 'Dry clean only', STD, 2, False),
    ('Embroidered Chiffon Formal Suit', 'FRM-02-GOLD-M', 'formals', None, ['formal-edit'], '14490.00', '16990.00', '15% OFF', 579, 1449, 2, '3 Piece - Shirt, Trouser & Dupatta', 'Embroidered Chiffon Shirt', 'Chiffon', 'Dry clean only', STD, 3, False),
    ('Net Formal Ensemble', 'FRM-03-PINK-M', 'formals', None, [], '16990.00', None, '', 679, 1699, 3, '3 Piece - Shirt, Trouser & Dupatta', 'Net Embellished Shirt', 'Net', 'Dry clean only', STD, 4, False),
    ('Velvet Formal Suit', 'FRM-04-WINE-M', 'formals', None, [], '18990.00', None, '', 759, 1899, 4, '2 Piece - Shirt & Trouser', 'Embellished Velvet Shirt', 'Velvet', 'Dry clean only', STD, 5, False),

    ('Embroidered Lawn Suit', 'EMB-01-BLACK-M', 'embroidered', 'lawn', ['new-arrivals'], '6990.00', None, '', 280, 699, 1, '2 Piece - Shirt & Trouser', 'Embroidered Lawn Shirt', 'Lawn', 'Hand wash recommended', STD, 5, True),
    ('Embroidered Chikankari Suit', 'EMB-02-WHITE-M', 'embroidered', None, ['fusion-edit'], '7990.00', '9990.00', '20% OFF', 320, 799, 2, '2 Piece - Shirt & Trouser', 'Chikankari Embroidered Shirt', 'Cotton', 'Hand wash recommended', STD, 6, True),
    ('Embroidered Net Kurti', 'EMB-03-PEACH-M', 'embroidered', None, ['fusion-edit'], '5490.00', None, '', 219, 549, 3, '1 Piece - Kurti', 'Embroidered Net Kurti', 'Net', 'Dry clean only', STD, 4, False),
    ('Embroidered Velvet Shawl Suit', 'EMB-04-MAROON-M', 'embroidered', None, [], '9990.00', None, '', 399, 999, 4, '3 Piece - Shirt, Trouser & Shawl', 'Embroidered Velvet Shirt', 'Velvet', 'Dry clean only', STD, 3, False),
]


def copy_seed_images():
    """Push the seed artwork into whatever storage backend is configured.

    Goes through `default_storage` rather than the filesystem so the same
    migration seeds a local `media/` directory in dev and a Cloudflare R2
    bucket in production. Existing keys are left alone, which keeps a re-run
    from overwriting artwork that has since been replaced in the admin.
    """
    for source in sorted(SEED_ASSETS.glob('*.webp')):
        key = 'products/{}'.format(source.name)
        if default_storage.exists(key):
            continue
        with source.open('rb') as handle:
            default_storage.save(key, ContentFile(handle.read()))


def seed(apps, schema_editor):
    copy_seed_images()

    Collection = apps.get_model('products', 'Collection')
    Fabric = apps.get_model('products', 'Fabric')
    Edit = apps.get_model('products', 'Edit')
    Product = apps.get_model('products', 'Product')

    collections = {row.slug: row for row in Collection.objects.all()}
    fabrics = {row.slug: row for row in Fabric.objects.all()}
    edits = {row.slug: row for row in Edit.objects.all()}

    # Stagger created_at a minute apart in catalogue order so `?sort=newest`
    # has something real to order by. auto_now_add overwrites an assigned
    # value, so it is written back with .update() after the insert.
    start = timezone.now() - datetime.timedelta(minutes=len(PRODUCTS))

    for index, row in enumerate(PRODUCTS):
        (
            name, sku, collection, fabric, edit_slugs, price, old_price,
            discount, reward_min, reward_max, image_no, composition,
            shirt_detail, fabric_label, wash_care, sizes, stock,
            is_best_seller,
        ) = row

        product, _ = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': name,
                'collection': collections[collection],
                'fabric': fabrics[fabric] if fabric else None,
                'price': price,
                'old_price': old_price,
                'discount': discount,
                'reward_min': reward_min,
                'reward_max': reward_max,
                'image': 'products/image-{}.webp'.format(image_no),
                'hover_image': 'products/image-{}-hover.webp'.format(image_no),
                'composition': composition,
                'shirt_detail': shirt_detail,
                'details': [
                    'Fabric: {}'.format(fabric_label),
                    'Wash Care: {}'.format(wash_care),
                    ORIGIN,
                ],
                'sizes': list(sizes),
                'stock': stock,
                'is_best_seller': is_best_seller,
                'is_active': True,
            },
        )
        product.edits.set([edits[slug] for slug in edit_slugs])
        Product.objects.filter(pk=product.pk).update(
            created_at=start + datetime.timedelta(minutes=index)
        )


def unseed(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    Product.objects.filter(sku__in=[row[1] for row in PRODUCTS]).delete()


class Migration(migrations.Migration):
    dependencies = [('products', '0003_alter_product_options')]
    operations = [migrations.RunPython(seed, unseed)]
