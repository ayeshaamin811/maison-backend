"""WSGI config for the Maison backend.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Media files.
#
# With R2 configured the browser fetches images straight from the bucket and
# this server never sees the request. Without it, product images live on local
# disk and something still has to serve them: Django's own static view is
# DEBUG-only, so in production /media/ would 404 and every product card would
# come up blank. WhiteNoise fills that gap.
#
# This is a fallback, not a destination. The files it serves sit on the
# container's disk, so anything uploaded through the admin is lost the next
# time the service redeploys. Only the seed artwork survives, and only because
# `manage.py seed_media` bakes it into the image at build time. Configure R2
# before anyone starts uploading real product photography.
from django.conf import settings  # noqa: E402

if not settings.USE_R2:
    from whitenoise import WhiteNoise  # noqa: E402

    application = WhiteNoise(application)
    application.add_files(str(settings.MEDIA_ROOT), prefix=settings.MEDIA_URL)
