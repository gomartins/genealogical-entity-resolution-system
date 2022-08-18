import unittest
from spacy_utils import SpacyUtils
import spacy

SPACY_POS_TAG_PROP = "tag_"
SPACY_POS_PROPER_NOUN = "NNP"
SPACY_POS_PRONOUN = 'PRON'
SPACY_POS_PARTICLE = 'PART'


class SpacyUtilsTest(unittest.TestCase):

    def setUp(self):
        nlp = spacy.load("en_core_web_trf")
        self.doc_1 = nlp("John went back with Ann because he was tired.")

    def test_find_elements(self):
        utils = SpacyUtils()
        span = list(self.doc_1.sents)[0]

        # In here we are starting at token 1, but we are looking back, so "John" is returned
        direction = "backward"
        start_at_token = 1
        results = utils.find_elements(span, start_at_token, direction, SPACY_POS_TAG_PROP, SPACY_POS_PROPER_NOUN)
        self.assertEqual(['John'], self.__tokens_to_text(results))

        # Same as above, but we start at the last token
        start_at_token = 5
        results = utils.find_elements(span, start_at_token, direction, SPACY_POS_TAG_PROP, SPACY_POS_PROPER_NOUN)
        self.assertEqual(['John', 'Ann'], self.__tokens_to_text(results))

    def test_find_element(self):
        utils = SpacyUtils()
        direction = "forward"
        span = list(self.doc_1.sents)[0]

        # Even though we should get both names here, this method returns only the first entry
        start_at_token = 0
        result = utils.find_element(span, start_at_token, direction, SPACY_POS_TAG_PROP, SPACY_POS_PROPER_NOUN, max_tokens=10)
        self.assertEqual('John', result.text)

    def test_find_element_backward(self):
        # Must be the small model
        nlp = spacy.load("en_core_web_sm")
        text = "Isaac Daniel Roosevelt (September 29, 1790 – December 24, 1863) was an American businessman " \
               "and the paternal grandfather of U.S. President Franklin D. Roosevelt."
        doc = nlp(text)
        utils = SpacyUtils()
        direction = "backward"
        span = list(doc.sents)[0]
        result = utils.find_element(span, 1, direction, SPACY_POS_TAG_PROP, SPACY_POS_PROPER_NOUN, max_tokens=10)
        self.assertEqual('Isaac', result.text)

    def __tokens_to_text(self, tokens):
        return [result.text for result in tokens]









