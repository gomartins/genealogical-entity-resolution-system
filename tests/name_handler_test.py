import unittest
import spacy
from name_handler import NameHandler
from constants import *


class NameHandlerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(NameHandlerTest, cls).setUpClass()
        NameHandlerTest.nlp = spacy.load("en_core_web_trf")

    def test_name_handler_lucretia(self):
        handler = NameHandler()
        name = self.__get_person('Lucretia "Loulie" (Wear) Walker')
        result = handler.to_person(name)
        self.assertEqual('Lucretia', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Walker', result.get(PERSON_LAST_NAME))
        self.assertEqual('Wear', result.get(PERSON_LAST_NAME_PRIOR_WEDDING))
        self.assertEqual('Loulie', result.get(PERSON_NICKNAME))
        self.assertEqual('F', result.get(PERSON_GENDER))
        self.assertEqual(None, result.get(PERSON_MIDDLE_NAMES))

    def test_name_handler_mary(self):
        handler = NameHandler()
        name = self.__get_person('Mary (née Isham) Randolph')
        result = handler.to_person(name)
        self.assertEqual('Mary', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Randolph', result.get(PERSON_LAST_NAME))
        self.assertEqual('Isham', result.get(PERSON_LAST_NAME_PRIOR_WEDDING))
        self.assertEqual('F', result.get(PERSON_GENDER))
        self.assertEqual(None, result.get(PERSON_MIDDLE_NAMES))

    def test_name_handler_abigail(self):
        handler = NameHandler()
        name = self.__get_person('Abigail (Smith) Adams')
        result = handler.to_person(name)
        self.assertEqual('Abigail', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Adams', result.get(PERSON_LAST_NAME))
        self.assertEqual('Smith', result.get(PERSON_LAST_NAME_PRIOR_WEDDING))
        self.assertEqual('F', result.get(PERSON_GENDER))
        self.assertEqual(None, result.get(PERSON_MIDDLE_NAMES))

    def test_name_handler_hellen(self):
        handler = NameHandler()
        name = self.__get_person('Ellen Bray (née Wrenshall) Dent')
        result = handler.to_person(name)
        self.assertEqual('Ellen', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Dent', result.get(PERSON_LAST_NAME))
        self.assertEqual('Wrenshall', result.get(PERSON_LAST_NAME_PRIOR_WEDDING))
        self.assertEqual('F', result.get(PERSON_GENDER))
        self.assertEqual(['Bray'], result.get(PERSON_MIDDLE_NAMES))

    def test_name_handler_marytje(self):
        handler = NameHandler()
        name = self.__get_person('Marytje (or Maria) Van Alen')
        result = handler.to_person(name)
        self.assertEqual('Marytje', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Alen', result.get(PERSON_LAST_NAME))
        # This is not exactly right - 'or' here means an alternative
        # name for Marytje, which we don't support at the moment
        self.assertEqual('Maria', result.get(PERSON_LAST_NAME_PRIOR_WEDDING))
        self.assertEqual('F', result.get(PERSON_GENDER))
        self.assertEqual(['Van'], result.get(PERSON_MIDDLE_NAMES))

    def test_name_handler_barbara(self):
        handler = NameHandler()
        name = self.__get_person('Barbara Jean (née Thompson')
        result = handler.to_person(name)
        self.assertEqual('Barbara', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Jean', result.get(PERSON_LAST_NAME))
        self.assertEqual('Thompson', result.get(PERSON_LAST_NAME_PRIOR_WEDDING))
        self.assertEqual('F', result.get(PERSON_GENDER))
        self.assertEqual(None, result.get(PERSON_MIDDLE_NAMES))

    def test_name_senior(self):
        handler = NameHandler()
        name = self.__get_person('Coolidge Senior')
        names_map = {'first_names': [], 'last_names': [], 'nicknames': []}
        result = handler.to_person(name, known_names_map=names_map)
        self.assertEqual('Coolidge', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Senior', result.get(PERSON_GEN_TITLE))

    def test_name_with_spaced_nickname(self):
        handler = NameHandler()
        name = self.__get_person('Theodore "T. R." Roosevelt Jr.')
        names_map = {'first_names': [], 'last_names': [], 'nicknames': []}
        result = handler.to_person(name, known_names_map=names_map)
        self.assertEqual('Theodore', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Roosevelt', result.get(PERSON_LAST_NAME))
        self.assertEqual('Jr', result.get(PERSON_GEN_TITLE))
        self.assertEqual('T. R.', result.get(PERSON_NICKNAME))

    def test_name_isaac_esq(self):
        handler = NameHandler()
        name = self.__get_person('Isaac Allerton Jr., Esq')
        names_map = {'first_names': [], 'last_names': [], 'nicknames': []}
        result = handler.to_person(name, known_names_map=names_map)
        self.assertEqual('Isaac', result.get(PERSON_FIRST_NAME))
        self.assertEqual('Allerton', result.get(PERSON_LAST_NAME))
        self.assertEqual('Jr', result.get(PERSON_GEN_TITLE))
        self.assertEqual('Esq', result.get(PERSON_OTHER_TITLE))

    def test_name_nee(self):
        handler = NameHandler()
        name = self.__get_person('née Walker')
        result = handler.to_person(name)
        self.assertEqual(None, result.get(PERSON_FIRST_NAME))
        self.assertEqual(None, result.get(PERSON_LAST_NAME))
        self.assertEqual('Walker', result.get(PERSON_LAST_NAME_PRIOR_WEDDING))
        self.assertEqual(None, result.get(PERSON_GENDER))
        self.assertEqual(None, result.get(PERSON_MIDDLE_NAMES))

    def __get_person(self, name):
        doc = NameHandlerTest.nlp(name)
        person = doc[:]
        attrs = {person: {}}
        return attrs


