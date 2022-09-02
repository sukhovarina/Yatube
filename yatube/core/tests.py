from http.client import NOT_FOUND

from django.test import Client, TestCase


class ViewTestClass(TestCase):
    def SetUp(self):
        self.client = Client()

    def test_error_page(self):
        """Cтраница 404 отдаёт кастомный шаблон."""
        response = self.client.get('/nonexist-page/')
        self.assertEqual(response.status_code, NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
