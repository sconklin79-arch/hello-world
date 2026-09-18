import unittest

from utils import average, divide, get_first, parse_int


class UtilsTest(unittest.TestCase):
    def test_average(self):
        self.assertEqual(average([1, 2, 3]), 2)
        with self.assertRaises(ValueError):
            average([])

    def test_get_first(self):
        self.assertEqual(get_first([1, 2, 3]), 1)
        with self.assertRaises(ValueError):
            get_first([])

    def test_parse_int(self):
        self.assertEqual(parse_int("42"), 42)
        with self.assertRaises(ValueError):
            parse_int("abc")

    def test_divide(self):
        self.assertEqual(divide(6, 3), 2)
        with self.assertRaises(ZeroDivisionError):
            divide(1, 0)


if __name__ == "__main__":
    unittest.main()
