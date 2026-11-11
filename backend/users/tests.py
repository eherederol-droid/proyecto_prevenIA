from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import User


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='http://localhost:3000/frontend',
)
class PasswordResetFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='athlete@example.com',
            password='Initial!Password2026',
            first_name='Test',
            last_name='Athlete',
        )

    def test_request_sends_reset_link_and_does_not_disclose_unknown_email(self):
        response = self.client.post(
            '/api/v1/auth/password-reset/',
            {'email': 'ATHLETE@example.com'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        link = next(
            line for line in mail.outbox[0].body.splitlines()
            if '/reset-password.html?' in line
        )
        self.assertTrue(link.startswith('http://localhost:3000/frontend/reset-password.html?'))
        self.assertIn('token', parse_qs(urlparse(link).query))

        unknown_response = self.client.post(
            '/api/v1/auth/password-reset/',
            {'email': 'unknown@example.com'},
        )
        self.assertEqual(unknown_response.status_code, 200)
        self.assertEqual(response.data, unknown_response.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_changes_password_and_token_cannot_be_reused(self):
        self.client.post('/api/v1/auth/password-reset/', {'email': self.user.email})
        link = next(
            line for line in mail.outbox[0].body.splitlines()
            if '/reset-password.html?' in line
        )
        query = parse_qs(urlparse(link).query)
        payload = {
            'uid': query['uid'][0],
            'token': query['token'][0],
            'new_password': 'Correct!HorseBattery2026',
            'password_confirm': 'Correct!HorseBattery2026',
        }

        response = self.client.post('/api/v1/auth/password-reset/confirm/', payload)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload['new_password']))

        repeated_response = self.client.post('/api/v1/auth/password-reset/confirm/', payload)
        self.assertEqual(repeated_response.status_code, 400)


class RegistrationFlowTests(APITestCase):
    def test_register_creates_account_and_returns_tokens(self):
        response = self.client.post('/api/v1/auth/register/', {
            'first_name': 'New',
            'last_name': 'Athlete',
            'email': 'new@example.com',
            'role': 'entrenador',
            'institution': 'Club',
            'specialty': '',
            'license_number': '',
            'password': 'Secure!Password2026',
            'password_confirm': 'Secure!Password2026',
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_register_returns_validation_errors(self):
        response = self.client.post('/api/v1/auth/register/', {
            'first_name': 'New',
            'last_name': 'Athlete',
            'email': 'invalid-email',
            'role': 'entrenador',
            'password': 'short',
            'password_confirm': 'different',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email='invalid-email').exists())


class AdminLoginTests(APITestCase):
    def test_active_superuser_can_log_in_with_email(self):
        User.objects.create_superuser(
            email='admin@example.com',
            password='Secure!AdminPassword2026',
            first_name='Admin',
            last_name='User',
        )

        response = self.client.post('/api/v1/auth/login/', {
            'email': 'admin@example.com',
            'password': 'Secure!AdminPassword2026',
        })

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
