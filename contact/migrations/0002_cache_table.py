"""Create the table behind the database cache.

DRF's throttling is cache-backed, and the cache is the database (see the CACHES
note in settings). Its table is not a model, so nothing creates it
automatically - it normally takes a separate `manage.py createcachetable` run,
which is one more step to remember and one more thing to get wrong on a fresh
environment. Without it every throttled view raises instead of responding.

Making it a migration ties the table to the schema, so any database the project
migrates has it. `createcachetable` skips a table that already exists, so this
is safe to re-run and safe alongside the pre-deploy invocation.

It lives in `contact` because that is the only app throttling anything today.
"""
from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command(
        'createcachetable',
        'django_cache',
        database=schema_editor.connection.alias,
        verbosity=0,
    )


def drop_cache_table(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS django_cache')


class Migration(migrations.Migration):
    dependencies = [('contact', '0001_initial')]
    operations = [migrations.RunPython(create_cache_table, drop_cache_table)]
