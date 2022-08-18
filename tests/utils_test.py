import unittest
from utils import Utils


class UtilsTest(unittest.TestCase):

    def test_merge_dictionaries(self):
        utils = Utils()
        data = [
            {'a': 'John', 'b': 'Doe'},
            {'c': 'Mary', 'd': 'Rose'}
        ]
        results = utils.merge_dictionaries(data)
        self.assertTrue(len(results) == 4)
        self.assertTrue(results['d'] == 'Rose')

    def test_equals_ignore_case(self):
        utils = Utils()
        self.assertTrue(utils.is_str_empty_or_equals_ignore_case("EQUALS", "equals"))
        self.assertTrue(utils.is_str_empty_or_equals_ignore_case("", ""))
        self.assertTrue(utils.is_str_empty_or_equals_ignore_case(None, None))
        self.assertFalse(utils.is_str_empty_or_equals_ignore_case("EQUALS_NOT", "equals"))
        self.assertFalse(utils.is_str_empty_or_equals_ignore_case("EQUALS_NOT", None))
        self.assertFalse(utils.is_str_empty_or_equals_ignore_case("EQUALS_NOT", ""))

    def test_most_frequent(self):
        utils = Utils()
        data = ['Apple', 'Banana', 'Apple', 'Strawberry']
        self.assertEqual('Apple', utils.most_frequent(data))

        # If there is a tie, returns the first match
        data = ['Apple', 'Banana', 'Apple', 'Strawberry', 'Banana']
        self.assertEqual('Banana', utils.most_frequent(data))

        # This is case sensitive!
        data = ['apple', 'Banana', 'Apple', 'Strawberry', 'Banana']
        self.assertEqual('Banana', utils.most_frequent(data))

        # This is NOT case sensitive. It returns the results in lower case!
        data = ['apple', 'Banana', 'Apple', 'Strawberry', 'Banana']
        self.assertEqual('banana', utils.most_frequent(data, case_sensitive=False))



