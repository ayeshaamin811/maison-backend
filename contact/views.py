import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .serializers import ContactMessageSerializer

logger = logging.getLogger(__name__)

SUCCESS_MESSAGE = "Thanks! We'll get back to you soon."


class ContactCreateView(CreateAPIView):
    """POST-only. Submissions are read in the Django admin, never over the API."""

    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contact'

    def initial(self, request, *args, **kwargs):
        # Temporary: the throttle counts per client identity, and behind a
        # proxy that identity comes from X-Forwarded-For. Logging what
        # actually arrives is the only way to know how many hops to trust.
        logger.info(
            'contact ident: xff=%r remote_addr=%r',
            request.META.get('HTTP_X_FORWARDED_FOR'),
            request.META.get('REMOTE_ADDR'),
        )
        super().initial(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # One shape for every failure: field name -> list of strings, so
            # the form can render each message under its own input.
            return Response(
                {'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        message = serializer.save()
        self.notify(message)
        return Response(
            {'success': True, 'message': SUCCESS_MESSAGE},
            status=status.HTTP_201_CREATED,
        )

    def notify(self, message):
        """Best-effort alert to whoever answers the inbox.

        The visitor's message is already saved by this point, so a mail
        failure must not turn a successful submission into an error they would
        retry. Anything that goes wrong is logged and swallowed.
        """
        recipient = getattr(settings, 'CONTACT_NOTIFY_EMAIL', '')
        if not recipient:
            return

        name = ' '.join(
            part for part in (message.first_name, message.last_name) if part
        )
        body = (
            'New contact form submission.\n\n'
            'Name:  {}\n'
            'Email: {}\n'
            'Sent:  {:%Y-%m-%d %H:%M} UTC\n\n'
            '{}\n'
        ).format(
            name or '(not given)',
            message.email,
            message.created_at,
            message.message or '(no message)',
        )

        try:
            send_mail(
                subject='Contact form: {}'.format(name or message.email),
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
            )
        except Exception:
            logger.exception(
                'Contact notification failed for message %s', message.pk
            )
