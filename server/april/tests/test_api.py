import unittest
from server.april.api import ApiClass  # Replace ApiClass with the actual class name from api.py

class TestApi(unittest.TestCase):

    def test_example(self):
        # Test that get_data method returns the correct data
        api_instance = ApiClass()
        expected_data = "expected data"
        self.assertEqual(api_instance.get_data(), expected_data)


if __name__ == '__main__':
    unittest.main()
