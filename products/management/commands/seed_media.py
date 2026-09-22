"""Put the seed product artwork into whatever storage backend is configured.

Migration 0004 does this too, but only the once - a redeployed container gets
a fresh, empty disk while the migration stays recorded as applied, so the
images it copied are gone and never come back. Running this at build time
bakes them into the image instead, and it is idempotent, so it is safe to run
on every deploy and safe to run by hand to restore artwork someone deleted.

With R2 configured this uploads to the bucket instead, where the problem does
not arise in the first place.
"""
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

SEED_ASSETS = Path(__file__).resolve().parents[2] / 'seed_assets'


class Command(BaseCommand):
    help = 'Copy the bundled seed product images into the media storage backend.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite images that are already present.',
        )

    def handle(self, *args, **options):
        if not SEED_ASSETS.is_dir():
            self.stderr.write('No seed_assets directory at {}'.format(SEED_ASSETS))
            return

        copied = skipped = 0
        for source in sorted(SEED_ASSETS.glob('*.webp')):
            key = 'products/{}'.format(source.name)
            exists = default_storage.exists(key)
            if exists and not options['force']:
                skipped += 1
                continue
            if exists:
                default_storage.delete(key)
            with source.open('rb') as handle:
                default_storage.save(key, ContentFile(handle.read()))
            copied += 1

        self.stdout.write(
            self.style.SUCCESS(
                'Seed media ready: {} copied, {} already present.'.format(
                    copied, skipped
                )
            )
        )
