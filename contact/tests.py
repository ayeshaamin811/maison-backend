"""Contract tests for the contact endpoint.

The response shapes are what the storefront form branches on, so they are
asserted literally rather than by status code alone.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ContactMessage

VALID = {
    'firstName': 'Ayesha',
    'lastName': 'Khan',
    'email': 'ayesha@example.com',
    'message': 'Do you restock the black cambric suit?',
}

# Throttling is cache-backed, so a test that posts more than once would
# otherwise inherit the previous test's counter.
NO_THROTTLE = {'DEFAULT_THROTTLE_RATES': {'contact': None}}
THROTTLED = {'DEFAULT_THROTTLE_RATES': {'contact': '5/hour'}}


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class ContactPostTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('contact-create')

    def test_valid_post_returns_201_and_the_success_shape(self):
        response = self.client.post(self.url, VALID, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {'success': True, 'message': "Thanks! We'll get back to you soon."},
        )

    def test_camelcase_keys_land_on_snake_case_fields(self):
        self.client.post(self.url, VALID, content_type='application/json')
        row = ContactMessage.objects.get()
        self.assertEqual(row.first_name, 'Ayesha')
        self.assertEqual(row.last_name, 'Khan')
        self.assertEqual(row.email, 'ayesha@example.com')
        self.assertEqual(row.message, VALID['message'])
        self.assertFalse(row.is_read)
        self.assertIsNotNone(row.created_at)

    def test_only_email_is_required(self):
        response = self.client.post(
            self.url, {'email': 'solo@example.com'}, content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        row = ContactMessage.objects.get()
        self.assertEqual(row.first_name, '')
        self.assertEqual(row.last_name, '')
        self.assertEqual(row.message, '')

    def test_empty_strings_are_accepted_for_the_optional_fields(self):
        response = self.client.post(
            self.url,
            {'firstName': '', 'lastName': '', 'email': 'a@b.com', 'message': ''},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)

    def test_whitespace_is_trimmed_on_every_field(self):
        self.client.post(
            self.url,
            {
                'firstName': '  Ayesha  ',
                'lastName': '\tKhan\n',
                'email': '  ayesha@example.com  ',
                'message': '   Hello there   ',
            },
            content_type='application/json',
        )
        row = ContactMessage.objects.get()
        self.assertEqual(row.first_name, 'Ayesha')
        self.assertEqual(row.last_name, 'Khan')
        self.assertEqual(row.email, 'ayesha@example.com')
        self.assertEqual(row.message, 'Hello there')

    def test_whitespace_only_optional_field_becomes_empty_not_blanks(self):
        self.client.post(
            self.url,
            {'firstName': '     ', 'email': 'a@b.com'},
            content_type='application/json',
        )
        self.assertEqual(ContactMessage.objects.get().first_name, '')

    def test_missing_email_is_a_400_in_the_errors_shape(self):
        response = self.client.post(
            self.url, {'message': 'hi'}, content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn('errors', body)
        self.assertIn('email', body['errors'])
        self.assertIsInstance(body['errors']['email'], list)
        self.assertIsInstance(body['errors']['email'][0], str)
        self.assertFalse(ContactMessage.objects.exists())

    def test_malformed_email_reports_under_the_email_key(self):
        response = self.client.post(
            self.url, {'email': 'not-an-email'}, content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {'errors': {'email': ['Enter a valid email address.']}},
        )

    def test_message_over_5000_chars_is_rejected_not_truncated(self):
        response = self.client.post(
            self.url,
            {'email': 'a@b.com', 'message': 'x' * 5001},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.json()['errors'])
        self.assertFalse(ContactMessage.objects.exists())

    def test_message_of_exactly_5000_chars_is_accepted(self):
        response = self.client.post(
            self.url,
            {'email': 'a@b.com', 'message': 'x' * 5000},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(ContactMessage.objects.get().message), 5000)

    def test_several_field_errors_come_back_together(self):
        response = self.client.post(
            self.url,
            {'email': 'bad', 'firstName': 'x' * 101, 'message': 'y' * 5001},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            sorted(response.json()['errors']),
            ['email', 'firstName', 'message'],
        )

    def test_form_encoded_bodies_work_too(self):
        response = self.client.post(self.url, VALID)
        self.assertEqual(response.status_code, 201)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_newest_first(self):
        for address in ['a@x.com', 'b@x.com', 'c@x.com']:
            self.client.post(
                self.url, {'email': address}, content_type='application/json'
            )
        self.assertEqual(
            [row.email for row in ContactMessage.objects.all()],
            ['c@x.com', 'b@x.com', 'a@x.com'],
        )


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class NotificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('contact-create')

    @override_settings(CONTACT_NOTIFY_EMAIL='inbox@maison.test')
    def test_a_notification_is_sent_when_an_address_is_configured(self):
        self.client.post(self.url, VALID, content_type='application/json')
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['inbox@maison.test'])
        self.assertIn('Ayesha', sent.subject)
        self.assertIn('ayesha@example.com', sent.body)
        self.assertIn('black cambric suit', sent.body)

    @override_settings(CONTACT_NOTIFY_EMAIL='')
    def test_nothing_is_sent_when_no_address_is_configured(self):
        response = self.client.post(self.url, VALID, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(CONTACT_NOTIFY_EMAIL='inbox@maison.test')
    def test_a_failing_mail_backend_does_not_break_the_201(self):
        """The message is already saved; a mail fault must not ask for a retry."""
        with patch('contact.views.send_mail', side_effect=OSError('smtp down')):
            with self.assertLogs('contact.views', level='ERROR'):
                response = self.client.post(
                    self.url, VALID, content_type='application/json'
                )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertEqual(ContactMessage.objects.count(), 1)


class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('contact-create')

    def tearDown(self):
        cache.clear()

    @override_settings(REST_FRAMEWORK=THROTTLED)
    def test_sixth_post_from_one_ip_is_throttled(self):
        for i in range(5):
            response = self.client.post(
                self.url,
                {'email': 'a{}@x.com'.format(i)},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 201, 'post {} rejected'.format(i))

        blocked = self.client.post(
            self.url, {'email': 'sixth@x.com'}, content_type='application/json'
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 5)

    @override_settings(REST_FRAMEWORK=THROTTLED)
    def test_the_limit_is_per_ip(self):
        for i in range(5):
            self.client.post(
                self.url,
                {'email': 'a{}@x.com'.format(i)},
                content_type='application/json',
            )
        other_ip = self.client.post(
            self.url,
            {'email': 'elsewhere@x.com'},
            content_type='application/json',
            REMOTE_ADDR='203.0.113.9',
        )
        self.assertEqual(other_ip.status_code, 201)

    @override_settings(REST_FRAMEWORK=THROTTLED)
    def test_invalid_posts_count_towards_the_limit(self):
        """Otherwise the limit is trivially bypassed by sending junk."""
        for _ in range(5):
            self.client.post(
                self.url, {'email': 'bad'}, content_type='application/json'
            )
        blocked = self.client.post(
            self.url, {'email': 'good@x.com'}, content_type='application/json'
        )
        self.assertEqual(blocked.status_code, 429)


class ContactAdminTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_superuser('staff', 'staff@example.com', 'pw')
        self.client.force_login(User.objects.get(username='staff'))
        self.rows = [
            ContactMessage.objects.create(email='a@x.com', message='first'),
            ContactMessage.objects.create(email='b@x.com', message='second'),
        ]

    def test_changelist_and_detail_render(self):
        self.assertEqual(
            self.client.get('/admin/contact/contactmessage/').status_code, 200
        )
        self.assertEqual(
            self.client.get(
                '/admin/contact/contactmessage/{}/change/'.format(self.rows[0].pk)
            ).status_code,
            200,
        )

    def test_mark_as_read_bulk_action(self):
        self.client.post(
            '/admin/contact/contactmessage/',
            {
                'action': 'mark_as_read',
                '_selected_action': [str(row.pk) for row in self.rows],
            },
            follow=True,
        )
        self.assertEqual(ContactMessage.objects.filter(is_read=True).count(), 2)

    def test_mark_as_unread_bulk_action(self):
        ContactMessage.objects.update(is_read=True)
        self.client.post(
            '/admin/contact/contactmessage/',
            {
                'action': 'mark_as_unread',
                '_selected_action': [str(self.rows[0].pk)],
            },
            follow=True,
        )
        self.assertFalse(ContactMessage.objects.get(pk=self.rows[0].pk).is_read)

    def test_messages_cannot_be_typed_in_by_hand(self):
        self.assertEqual(
            self.client.get('/admin/contact/contactmessage/add/').status_code, 403
        )
