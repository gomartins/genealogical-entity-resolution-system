import unittest
from regex_handler import RegexHandler


class RegexHandlerTest(unittest.TestCase):

    def test_regex_positive(self):
        handler = RegexHandler()
        handler.add_rule("any_id", "This (should) match", 1)  # rule is ignore case by default
        handler.add_rule("any_other_id", "This (should) (match)", 2)
        output = handler.execute("This SHOULD match")
        self.assertEqual(output['any_id'], ['SHOULD'])
        self.assertEqual(output['any_other_id'], ['match'])

    def test_regex_negative(self):
        handler = RegexHandler()
        handler.add_rule("any_id", "This (should) match", 1)
        handler.add_rule("any_other_id", "This (should) (match)", 2)
        output = handler.execute("This should NOT match")  # NOT
        self.assertTrue(len(output) == 0)

    def test_regex_normalizer(self):
        print("To be done")
        self.assertTrue(True)



