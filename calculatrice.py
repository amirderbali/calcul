import unittest
from test import addition, soustraction, multiplication

class TestCalculator(unittest.TestCase):

    def test_addition(self):
        self.assertEqual(addition(2, 3), 5)

    def test_soustraction(self):
        self.assertEqual(soustraction(5, 3), 1)

    def test_multiplication(self):
        self.assertEqual(multiplication(2, 4), 8)

if __name__ == '__main__':
    unittest.main()