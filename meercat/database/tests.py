from django.test import TestCase

# Create your tests here.
class TestTest(TestCase):

    def test_passing_test(self):
        self.assertIs(True, True)

    def test_failing_test(self):
        self.assertIs(False, True)