import unittest

import spacy

from named_entity_recognition import PersonRecognition
from relation_extraction import *
from relation_extraction import RelationExtraction
from spacy_utils import SpacyUtils

config = ConfigHandler()

NAMED_SPAN_PERSON = config.get('SPACY_NAMED_SPAN_PERSON')

TEXT_1 = "Michelle LaVaughn Robinson Obama (née Robinson; born January 17, 1964) is an American " \
         "attorney and author who served as the First Lady of the United States from 2009 to 2017. She " \
         "was the first African-American woman to serve in this position. She is married to the 44th " \
         "President of the United States, Barack Obama."

TEXT_2 = "Craig Malcolm Robinson was born on April 21, 1962, in Calumet Park, Illinois, to Fraser Robinson, " \
         "a city water plant employee and Democratic precinct captain, and Marian Robinson (née Shields), a " \
         "secretary at Spiegel's catalog store."

TEXT_3 = "Captain Hancock Lee (born 1653 - May 25, 1709)  was an American colonial politician. He was a member " \
         "of the House of Burgesses, a Justice of Northampton County, and a naval officer. Hancock Lee was born to " \
         "Richard Lee, Esq., in 1653. He was justice in Northampton County in 1677, then moved to Northumberland " \
         "County where he was justice in 1687."

TEXT_4 = "He was the fourth child and third eldest son of Col. John Dandridge Jr. and his wife Frances Jones."

TEXT_5 = "William Madison (May 5, 1762 – July 20, 1843) was an American general. He served in the American " \
         "Revolutionary War and War of 1812. Son of James Madison Sr. and Eleanor Rose Conway, he was the younger " \
         "brother of James Madison, fourth President of the United States. Madison married Frances Throckmorton and " \
         "had eleven children. He was the grandfather of Confederate Brigadier-General James E. Slaughter."

TEXT_6 = "He was born on March 17, 1877 to Nellie Grant and Algernon Charles Frederick Sartoris in Washington, DC."

TEXT_7 = "Kennedy had an elder brother, Joseph Jr., and seven younger siblings: Rosemary, Kathleen (\"Kick\"), " \
         "Eunice, Patricia, Robert (\"Bobby\"), Jean, and Edward (\"Ted\")."

TEXT_8 = "Through his son William, George Steptoe Washington was the grandfather of Jane Washington (b. 1834), " \
         "who married Thomas Gascoigne Moncure (1837–1906) and had no issue; Lucy Washington (1822–1825), " \
         "who died young; Millissent Fowler Washington (1824–1893), who married Robert Grier McPherson (1819–1899) " \
         "and had issue; William Temple Washington, Jr. (b. 1827); Thomas West Washington (1829–1868); Eugenia " \
         "Scholay Washington (1838–1900), a founder of the lineage societies, Daughters of the American Revolution " \
         "and Daughters of the Founders and Patriots of America; and Ferdinand Steptoe Washington (1843–1912). "

TEXT_9 = "George Washington (February 22, 1732 – December 14, 1799) was an American political leader, " \
         "military general, statesman, and Founding Father who served as the first president of the United States " \
         "from 1789 to 1797. "


class AttrResolversTest(unittest.TestCase):

    def setUp(self):
        self.norm_rel = RelationshipNormalizer()
        self.norm_month = MonthAttributeNormalizer()
        self.mask = PersonMaskerizer()
        self.norm_born_first = BornToNormalizer(False)
        self.norm_born_second = BornToNormalizer(True)
        self.norm_married = MarriedNormalizer()

    @classmethod
    def setUpClass(cls):
        super(AttrResolversTest, cls).setUpClass()
        AttrResolversTest.nlp = spacy.load("en_core_web_trf")

    def execute(self, resolver, text, span_idx):
        doc = self.__get_doc(text)
        person = doc.spans[NAMED_SPAN_PERSON][span_idx]
        return resolver.execute(person)

    def test_date_of_birth_resolver(self):
        resolver = AttrResolverGroup(min_ents=1, max_tokens=10, mode="after_span")
        resolver.add_expr("yob", REGEX_BORN_YEAR, 1)
        resolver.add_expr("mob", REGEX_BORN_MONTH, 1, normalizer=self.norm_month)
        resolver.add_expr("dob", REGEX_BORN_DAY, 1)

        result = self.execute(resolver, TEXT_1, 0)
        self.assertEqual(result['yob'], ['1964'])
        self.assertEqual(result['mob'], [1])
        self.assertEqual(result['dob'], ['17'])

        result = self.execute(resolver, TEXT_2, 0)
        self.assertEqual(result['yob'], ["1962"])
        self.assertEqual(result['mob'], [4])
        self.assertEqual(result['dob'], ["21"])

        result = self.execute(resolver, TEXT_3, 0)
        self.assertEqual(result['yob'], ["1653"])

        result = self.execute(resolver, TEXT_6, 0)
        self.assertEqual(result['yob'], ["1877"])
        self.assertEqual(result['mob'], [3])
        self.assertEqual(result['dob'], ["17"])

    def test_relationship_resolver(self):
        resolver = AttrResolverGroup(min_ents=2, max_tokens=1000, mode="start_sent")
        resolver.add_expr(id="rel", expr=REGEX_PERSON_MARRY, group=1, mask=self.mask, normalizer=self.norm_rel)
        result = self.execute(resolver, TEXT_1, 3)
        self.assertEqual(result['rel'][0], "[243:246],spouse_of,[302:314]")

    def test_person_relatives(self):
        resolver = AttrResolverGroup(min_ents=2, max_tokens=1000, mode="start_span")
        resolver.add_expr(id="rel", expr=REGEX_PERSON_RELATIVES, group=1, mask=self.mask, normalizer=self.norm_rel)
        result = self.execute(resolver, TEXT_4, 2)
        self.assertEqual(result['rel'][0], "[76:79],spouse_of,[85:98]")

    def test_person_relatives_again(self):
        resolver = AttrResolverGroup(min_ents=2, max_tokens=1000, mode="start_span")
        resolver.add_expr(id="rel", expr=REGEX_PERSON_RELATIVES, group=1, mask=self.mask, normalizer=self.norm_rel)
        result = self.execute(resolver, TEXT_5, 4)
        self.assertEqual(result['rel'][0], "[182:184],sibling_of,[212:225]")

    def test_relationship_parent_resolver(self):
        res = AttrResolverGroup(min_ents=2, max_tokens=1000, mode="start_sent")
        res.add_expr(id="rel", expr=REGEX_PERSON_BORN_TO, group=1, mask=self.mask, normalizer=self.norm_born_first)
        result = self.execute(res, TEXT_2, 0)
        self.assertEqual(result['rel'][0], "[0:22],child_of,[81:96]")

        res = AttrResolverGroup(min_ents=3, max_tokens=1000, mode="start_sent")
        res.add_expr(id="rel", expr=REGEX_PERSON_BORN_TO_PAIR, group=1, mask=self.mask, normalizer=self.norm_born_first)
        res.add_expr(id="rel", expr=REGEX_PERSON_BORN_TO_PAIR, group=1, mask=self.mask, normalizer=self.norm_born_second)
        result = self.execute(res, TEXT_2, 0)
        self.assertEqual(result['rel'][0], "[0:22],child_of,[81:96]")
        self.assertEqual(result['rel'][1], "[0:22],child_of,[163:178]")

        result = self.execute(res, TEXT_6, 0)
        self.assertEqual(result['rel'][0], "[0:2],child_of,[33:45]")
        self.assertEqual(result['rel'][1], "[0:2],child_of,[50:85]")

    def test_last_name_before_wedding(self):
        resolver = AttrResolverGroup(min_ents=1, max_tokens=4, mode="after_span")
        resolver.add_expr(id="nee", expr=REGEX_NAME_NEE, group=1)
        result = self.execute(resolver, TEXT_1, 0)
        self.assertEqual(["Robinson"], result['nee'])

    def test_son_relationship(self):
        text = "John Paul was the son of Warren William and Paula Maria"
        rel_pair_res = AttrResolverGroup(min_ents=3, max_tokens=1000, mode="start_span")
        rel_norm_2nd = RelationshipNormalizer(target_second_person=True)
        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_CHILDREN_PAIR, group=1, mask=self.mask, normalizer=self.norm_rel)
        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_CHILDREN_PAIR, group=1, mask=self.mask, normalizer=rel_norm_2nd)
        result = self.execute(rel_pair_res, text, 0)
        self.assertEqual(result['rel'][0], "[0:9],child_of,[25:39]")
        self.assertEqual(result['rel'][1], "[0:9],child_of,[44:55]")

    def test_afterwards_nickname(self):
        resolver = AttrResolverGroup(min_ents=1, max_tokens=4, mode="after_span")
        resolver.add_expr("nickname", REGEX_ENCLOSED_BY_DB_QUOTES, 1)
        doc = self.__get_doc(TEXT_7)
        person = doc.spans[NAMED_SPAN_PERSON][3]
        result = resolver.execute(person)
        self.assertEqual(result['nickname'], ['Kick'])

    def test_multiple_dates(self):
        doc = self.__get_doc(TEXT_8)
        spans = doc.spans[NAMED_SPAN_PERSON]
        entry = spans[8]
        re = RelationExtraction()
        result = re.extract(spans)
        entry_result = result[entry]
        self.assertEqual(len(entry_result['yob']), 1)
        self.assertEqual(result[entry]['yob'][0], '1827')

    def test_married_sentence(self):
        text = "Gannett was married to Sarah Alden Derby"
        resolver = AttrResolverGroup(min_ents=2, max_tokens=1000, mode="start_span")
        resolver.add_expr(id="rel", expr=REGEX_PERSON_MARRY, group=1, mask=self.mask, normalizer=self.norm_rel)
        result = self.execute(resolver, text, 0)
        self.assertEqual(result['rel'][0], "[0:7],spouse_of,[23:40]")

    def test_married_sentence_again(self):
        text = "Fannie Josephine (1857–1909), married Ulysses S. Grant, Jr."
        resolver = AttrResolverGroup(min_ents=2, max_tokens=1000, mode="start_span")
        resolver.add_expr(id="rel", expr=REGEX_PERSON_MARRY, group=1, mask=self.mask, normalizer=self.norm_rel)
        result = self.execute(resolver, text, 0)
        self.assertEqual(result['rel'][0], "[0:16],spouse_of,[38:59]")

    def __get_doc(self, text):
        doc = AttrResolversTest.nlp(text)
        person_name_spans = PersonRecognition().get_person_spans(doc)
        SpacyUtils().initialize_person_entities(doc, person_name_spans)
        return doc
