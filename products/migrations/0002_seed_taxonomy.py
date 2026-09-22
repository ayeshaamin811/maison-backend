"""Seed the 15 taxonomy rows.

The slugs are already live in storefront URLs, so they are fixed values, not
editable content. Names are display-only and safe to change in admin later.
"""
from django.db import migrations

COLLECTIONS = [
    ('solids', 'Solids'),
    ('embroidered', 'Embroidered'),
    ('unstitched', 'Unstitched'),
    ('casual', 'Casual'),
    ('west', 'West'),
    ('formals', 'Formals'),
]

FABRICS = [
    ('lawn', 'Lawn'),
    ('crepe', 'Crepe'),
    ('matte-twill', 'Matte Twill'),
    ('linen', 'Linen'),
    ('silk', 'Silk'),
]

EDITS = [
    ('new-arrivals', 'New Arrivals'),
    ('formal-edit', 'Formal Edit'),
    ('co-ordsets', 'Co-ord Sets'),
    ('fusion-edit', 'Fusion Edit'),
]

GROUPS = [('Collection', COLLECTIONS), ('Fabric', FABRICS), ('Edit', EDITS)]


def seed(apps, schema_editor):
    for model_name, rows in GROUPS:
        model = apps.get_model('products', model_name)
        for slug, name in rows:
            model.objects.update_or_create(slug=slug, defaults={'name': name})


def unseed(apps, schema_editor):
    for model_name, rows in GROUPS:
        model = apps.get_model('products', model_name)
        model.objects.filter(slug__in=[slug for slug, _ in rows]).delete()


class Migration(migrations.Migration):
    dependencies = [('products', '0001_initial')]
    operations = [migrations.RunPython(seed, unseed)]
