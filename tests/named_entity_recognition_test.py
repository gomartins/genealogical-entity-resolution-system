import unittest

import spacy

from named_entity_recognition import PersonRecognition


class NamedEntityRecognitionTest(unittest.TestCase):

    def setUp(self):
        self.nlp = spacy.load("en_core_web_trf")

    def test_sentence(self):
        text = "They had a son, Herbert Charles Urban Grant Sartoris."
        doc = self.__get_doc(text)
        person_spans = PersonRecognition().get_person_spans(doc)
        self.assertEqual('Herbert Charles Urban Grant Sartoris', str(person_spans[0]))

    def test_other_sentence(self):
        # must be the small model
        self.nlp = spacy.load("en_core_web_sm")
        text = "In January 1795, Hamilton, who desired more income for his family, resigned office and was replaced " \
               "by Washington appointment Oliver Wolcott, Jr. "
        doc = self.__get_doc(text)
        person_spans = PersonRecognition().get_person_spans(doc)
        self.assertEqual('Oliver Wolcott, Jr.', str(person_spans[2]))

    def test_sentence_with_disease_name(self):
        text = "Kennedy was 30 and in his first term in Congress, he was diagnosed by Sir Daniel Davis at The London " \
               "Clinic with Addison's disease, a rare endocrine disorder. "
        doc = self.__get_doc(text)
        person_spans = PersonRecognition().get_person_spans(doc)
        # Should not consider Addison as a name
        self.assertEqual(len(person_spans), 4)

    def test_hayes_again(self):
        text = "His uncle Sardis Birchard died that year, and the Hayes family moved into Spiegel Grove"
        doc = self.__get_doc(text)
        person_spans = PersonRecognition().get_person_spans(doc)
        # Should not consider Hayes as a name
        self.assertEqual(len(person_spans), 2)

    def test_nicknames(self):
        text = "Kennedy had an elder brother, Joseph Jr., and seven younger siblings: Rosemary, Kathleen (\"Kick\"), " \
               "Eunice, Patricia, Robert (\"Bobby\"), Jean, and Edward (\"Ted\")."
        doc = self.__get_doc(text)
        person_spans = PersonRecognition().get_person_spans(doc)
        # Nicknames should not be captured here, they are treated by the RE component
        self.assertEqual(len(person_spans), 9)

    def __get_doc(self, text):
        doc = self.nlp(text)
        return doc
