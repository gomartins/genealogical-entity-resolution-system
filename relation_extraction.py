import logging
import regex_handler
from spacy_utils import SpacyUtils
from regex_constants import *
from constants import *
from utils import Utils

logger = logging.getLogger('logger')

rel_map = {'married': 'spouse_of',
           'remarried': 'spouse_of',
           'wife': 'spouse_of',
           'husband': 'spouse_of',
           'sister': 'sibling_of',
           'brother': 'sibling_of',
           'father': 'father_of',
           'grandfather': 'grandfather_of',
           'mother': 'mother_of',
           'grandmother': 'grandmother_of',
           'son': 'child_of',
           'grandson': 'grandson_of',
           'daughter': 'child_of',
           'granddaughter': 'granddaughter_of',
           'born': 'child_of',
           'parents': 'child_of',
           'cousin': 'cousin_of',
           'uncle': 'uncle_of',
           'aunt': 'aunt_of',
           'nephew': 'nephew_of',
           'niece': 'niece_of',
           }

spacy_utils = SpacyUtils()


class RelationExtraction(object):
    """
    This class is responsible for identifying relationships for person entities.
    It should return a dictionary with its key containing the start/end of a token,
    and its value containing the list of relationships, as per the following:

    {
        [0:8]: {'year_of_birth': 1987, 'month_of_birth': 03}
    }
    """

    def __init__(self):
        self.resolvers = self.__get_resolvers()

    def extract(self, person_spans):
        relationships = {}
        for person_span in person_spans:
            results = []
            for resolver in self.resolvers:
                logger.debug("Executing resolver for person_span: %s", person_span)
                res = resolver.execute(person_span)
                logger.debug("Successfully executed resolver for person %s: %s", person_span, res)
                if res:
                    results.append(res)
            relationships[person_span] = Utils.merge_dictionaries(results)
        return relationships

    def __get_resolvers(self):
        resolvers = []

        attr_res = AttrResolverGroup(min_ents=1, max_tokens=4, mode="after_span", person_only=True)
        attr_res.add_expr(id="nee", expr=REGEX_NAME_NEE, group=1)
        attr_res.add_expr(id="nickname", expr=REGEX_ENCLOSED_BY_DB_QUOTES, group=1)
        resolvers.append(attr_res)

        month_norm = MonthAttributeNormalizer()
        date_res = AttrResolverGroup(min_ents=1, max_tokens=10, mode="after_span", stop_before_next_ent=True)
        date_res.add_expr(id="yob", expr=REGEX_YOB_YOD_PATTERN, group=1, desc="Matches (1942–1995), Captures 1942")
        date_res.add_expr(id="yob", expr=REGEX_BORN_YEAR, group=1, desc="Matches (born 1998), (b. July 30, 1998) - Captures 1998")
        date_res.add_expr(id="yob", expr=REGEX_BORN_IN_YEAR, group=1, desc="Matches (born in 1928) - Captures 1928")
        date_res.add_expr(id="yod", expr=REGEX_YOB_YOD_PATTERN, group=2, desc="Matches (1942–1995) - Captures 1995")
        date_res.add_expr(id="yod", expr=REGEX_DIED_IN_YEAR, group=1, desc="Matches (died in 1928) - Captures 1928")
        date_res.add_expr(id="mob", expr=REGEX_BORN_MONTH, group=1, normalizer=month_norm, desc="Matches (born August 4, 1961), (b. August 30, 1937) - Captures August")
        date_res.add_expr(id="dob", expr=REGEX_BORN_DAY, group=1, desc="Matches (born August 4, 1961), (b. July 4, 1937) - Captures 4")

        # For (May 5, 1762 – July 20, 1843)
        date_res.add_expr(id="mob", expr=REGEX_FULL_DOB_DOD_PATTERN, group=1, normalizer=month_norm)
        date_res.add_expr(id="dob", expr=REGEX_FULL_DOB_DOD_PATTERN, group=2)
        date_res.add_expr(id="yob", expr=REGEX_FULL_DOB_DOD_PATTERN, group=3)
        date_res.add_expr(id="mod", expr=REGEX_FULL_DOB_DOD_PATTERN, group=4, normalizer=month_norm)
        date_res.add_expr(id="dod", expr=REGEX_FULL_DOB_DOD_PATTERN, group=5)
        date_res.add_expr(id="yod", expr=REGEX_FULL_DOB_DOD_PATTERN, group=6)

        # For (25 December 1737 – 18 April 1785)
        date_res.add_expr(id="dob", expr=REGEX_FULL_DOB_DOD_DF_PATTERN, group=1)
        date_res.add_expr(id="mob", expr=REGEX_FULL_DOB_DOD_DF_PATTERN, group=2, normalizer=month_norm)
        date_res.add_expr(id="yob", expr=REGEX_FULL_DOB_DOD_DF_PATTERN, group=3)
        date_res.add_expr(id="dod", expr=REGEX_FULL_DOB_DOD_DF_PATTERN, group=4)
        date_res.add_expr(id="mod", expr=REGEX_FULL_DOB_DOD_DF_PATTERN, group=5, normalizer=month_norm)
        date_res.add_expr(id="yod", expr=REGEX_FULL_DOB_DOD_DF_PATTERN, group=6)

        # For (born 1653 - May 25, 1709) or (1653 - May 25, 1709)
        date_res.add_expr(id="yob", expr=REGEX_YOB_DOD_PATTERN, group=1)
        date_res.add_expr(id="mod", expr=REGEX_YOB_DOD_PATTERN, group=2, normalizer=month_norm)
        date_res.add_expr(id="dod", expr=REGEX_YOB_DOD_PATTERN, group=3)
        date_res.add_expr(id="yod", expr=REGEX_YOB_DOD_PATTERN, group=4)

        # For (May 13, 1744 – May 1786)
        date_res.add_expr(id="mob", expr=REGEX_FULL_DOB_PARTIAL_DOD, group=1, normalizer=month_norm)
        date_res.add_expr(id="dob", expr=REGEX_FULL_DOB_PARTIAL_DOD, group=2)
        date_res.add_expr(id="yob", expr=REGEX_FULL_DOB_PARTIAL_DOD, group=3)
        date_res.add_expr(id="mod", expr=REGEX_FULL_DOB_PARTIAL_DOD, group=4, normalizer=month_norm)
        date_res.add_expr(id="yod", expr=REGEX_FULL_DOB_PARTIAL_DOD, group=5)

        # For (January 26, 1644-1695)
        date_res.add_expr(id="mob", expr=REGEX_FULL_DOB_YOD, group=1, normalizer=month_norm)
        date_res.add_expr(id="dob", expr=REGEX_FULL_DOB_YOD, group=2)
        date_res.add_expr(id="yob", expr=REGEX_FULL_DOB_YOD, group=3)
        date_res.add_expr(id="yod", expr=REGEX_FULL_DOB_YOD, group=4)

        resolvers.append(date_res)

        rel_res = AttrResolverGroup(min_ents=2, max_tokens=1000, mode="start_span")
        mask = PersonMaskerizer()
        rel_norm = RelationshipNormalizer()
        rel_res.add_expr(id="rel", expr=REGEX_PERSON_MARRY, group=1, mask=mask, normalizer=rel_norm)
        rel_res.add_expr(id="rel", expr=REGEX_PERSON_RELATIVES, group=1, mask=mask, normalizer=rel_norm)


        born_to_norm = BornToNormalizer(False)
        rel_res.add_expr(id="rel", expr=REGEX_PERSON_BORN_TO, group=1, mask=mask, normalizer=born_to_norm)
        resolvers.append(rel_res)

        rel_res_alt = AttrResolverGroup(min_ents=2, max_tokens=20, mode="start_span", force_max_tokens=True)
        rel_res_alt.add_expr(id="rel", expr=REGEX_PERSON_MARRY_ALT, group=1, mask=mask, normalizer=rel_norm)
        resolvers.append(rel_res_alt)

        # We execute the following twice to capture both parents
        rel_pair_res = AttrResolverGroup(min_ents=3, max_tokens=1000, mode="start_span")
        born_to_norm_2nd = BornToNormalizer(True)
        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_BORN_TO_PAIR, group=1, mask=mask, normalizer=born_to_norm)
        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_BORN_TO_PAIR, group=1, mask=mask, normalizer=born_to_norm_2nd)

        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_PARENTS_PAIR, group=1, mask=mask, normalizer=born_to_norm)
        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_PARENTS_PAIR, group=1, mask=mask, normalizer=born_to_norm_2nd)

        rel_norm_2nd = RelationshipNormalizer(target_second_person=True)
        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_CHILDREN_PAIR, group=1, mask=mask, normalizer=rel_norm)
        rel_pair_res.add_expr(id="rel", expr=REGEX_PERSON_CHILDREN_PAIR, group=1, mask=mask, normalizer=rel_norm_2nd)

        resolvers.append(rel_pair_res)
        return resolvers


class AttrResolverGroup(object):

    def __init__(self, min_ents=None, mode="after", max_tokens=None, person_only=False, stop_before_next_ent=False,
                 force_max_tokens=False):
        self.handler = regex_handler.RegexHandler()
        self.min_entities = min_ents
        # Truncate the text to prevent capturing data from other entities? Defaults to False
        self.stop_before_next_ent = stop_before_next_ent
        self.mode = mode
        # Person only or also pronouns?
        self.person_only = person_only
        self.max_tokens = max_tokens
        self.force_max_tokens = force_max_tokens

    def __get_starting_point(self, span):
        if self.mode == "after_span":
            return span.end
        elif self.mode == "start_span":
            return span.start
        elif self.mode == "start_sent":
            return span.sent.start

    def add_expr(self, id=None, expr=None, group=0, normalizer=None, mask=None, postprocessor=None, desc=None):
        self.handler.add_rule(id, expr, group, normalizer=normalizer, maskerizer=mask, postprocessor=postprocessor, desc=desc)

    def execute(self, span):
        if self.person_only and str(span).lower() in PRONOUNS:
            return

        logger.debug("Checking if at least %s entities are found for %s in sentence [%s]", self.min_entities, span.sent)
        ents = list(set(filter(None, [token._.get_person for token in span.sent])))

        logger.debug("# of entities found: %s", len(ents))
        if len(ents) < self.min_entities:
            return

        start = self.__get_starting_point(span)
        sorted_ents = sorted(ents, key=lambda k: k.start)
        next_ent = sorted_ents.index(span) + (self.min_entities - 1)

        try:
            next_ent_start = sorted_ents[sorted_ents.index(span) + 1].start
        except IndexError:
            next_ent_start = 0

        if len(ents) > 1 and self.stop_before_next_ent and next_ent_start > 0 and not self.force_max_tokens:
            found_span = span.sent.doc[start:next_ent_start] \
                if (next_ent_start - start) < self.max_tokens \
                else span.doc[start:span.end + self.max_tokens]
        elif self.min_entities != 1 and len(sorted_ents) - 1 >= next_ent and not self.force_max_tokens:
            found_span = span.sent.doc[start:sorted_ents[next_ent].end]
        else:
            found_span = span.doc[start:span.sent.end] \
                if (span.sent.end - span.end) < self.max_tokens \
                else span.doc[start:span.end + self.max_tokens]

        text_span = str(found_span).strip()
        if not text_span or text_span == '.':
            return
        logger.debug("Executing pattern for span [%s] against text [%s] with original sentence [%s]", span, found_span, span.sent)
        return self.handler.execute(found_span)


class MonthAttributeNormalizer(object):

    def normalize(self, span=None, result=None):
        if isinstance(result, int) or result.isdigit():
            return int(result)
        key = str(result).upper()[0:3]
        if key in MONTH_MAP:
            return MONTH_MAP[key]


class PersonMaskerizer(object):

    def apply_mask(self, span):
        tokens_to_mask = set()
        for token in span:
            if spacy_utils.get_attr(token=token, attr_name='is_person_part', ext=True):
                tokens_to_mask.add(token)
        masked_text = ""
        should_add = True
        for token in span:
            if not should_add and token in tokens_to_mask:
                continue
            if token in tokens_to_mask:
                masked_text += '_PERSON_'
                masked_text += token.whitespace_
                should_add = False
            else:
                masked_text += token.text_with_ws
                should_add = True
        return masked_text


class BornToNormalizer(object):

    def __init__(self, target_second_person):
        self.target_second_person = target_second_person

    def is_nominal_subject(self, person):
        return any(token.dep_ == 'nsubj' for token in person)

    def normalize(self, span=None, result=None):
        logger.debug("Postprocessing result for [%s] and [%s]", span, result)
        match = spacy_utils.find_element(span=span, start_at=span.start, mode="forward", attr_key="text",
                                         attr_val=result, max_tokens=100)
        if not match:
            logger.debug("Could not find match for: %s", result)
            return None
        left = spacy_utils.find_element(span=match.sent, start_at=match.i, mode="backward", attr_key="is_person_part",
                                        attr_val=True, max_tokens=15, ext=True)
        right = None
        if not self.target_second_person:
            right = spacy_utils.find_element(span=match.sent, start_at=match.i, mode="forward",
                                             attr_key="is_person_part", attr_val=True, max_tokens=15, ext=True)
        else:
            right = spacy_utils.find_elements(span=match.sent, start_at=match.i, mode="forward",
                                              attr_key="is_person_part", attr_val=True, max_tokens=30, ext=True)[-1]

        logger.debug("Found entities: [%s] and [%s]", left, right)
        if left and right:
            left_final = spacy_utils.get_span_range(left._.get_person)
            right_final = spacy_utils.get_span_range(right._.get_person)
            rel_mapping = rel_map[result.strip().lower()]
            result = "[{0}],{1},[{2}]".format(left_final, rel_mapping, right_final)
            return result
        else:
            logger.debug("Could not find one of the sides in the relationship")


class RelationshipNormalizer(object):

    def __init__(self, target_second_person=False):
        self.target_second_person = target_second_person

    def is_nominal_subject(self, person):
        return any(token.dep_ == 'nsubj' for token in person)

    def is_possessive(self, person):
        return any(token.dep_ == 'poss' for token in person)

    def normalize(self, span=None, result=None):
        logger.debug("Postprocessing result for [%s] and [%s]", span, result)
        match = spacy_utils.find_element(span=span, start_at=span.start, mode="forward", attr_key="text",
                                         attr_val=result, max_tokens=100)
        if not match:
            logger.debug("Could not find match for: %s", result)
            return None

        left = spacy_utils.find_element(span=span, start_at=match.i, mode="backward", attr_key="is_person_part",
                                        attr_val=True, max_tokens=15, ext=True)

        right = None
        if not self.target_second_person:
            right = spacy_utils.find_element(span=match.sent, start_at=match.i, mode="forward",
                                             attr_key="is_person_part", attr_val=True, max_tokens=15, ext=True)
        else:
            right = spacy_utils.find_elements(span=match.sent, start_at=match.i, mode="forward",
                                              attr_key="is_person_part", attr_val=True, max_tokens=30, ext=True)
            if right:
                right = right[-1]

        logger.debug("Found entities: [%s] and [%s]", left, right)
        if left and right:
            person_left = left._.get_person
            person_right = right._.get_person
            left_final = spacy_utils.get_span_range(person_left)
            right_final = spacy_utils.get_span_range(person_right)
            rel_mapping = rel_map[result.strip().lower()]
            result = None
            if self.is_nominal_subject(person_left) or self.is_possessive(person_left):
                result = "[{0}],{1},[{2}]".format(left_final, rel_mapping, right_final)
            elif self.is_nominal_subject(person_right) or self.is_possessive(person_right):
                result = "[{0}],{1},[{2}]".format(right_final, rel_mapping, left_final)
            else:
                result = "[{0}],{1},[{2}]".format(left_final, rel_mapping, right_final)
            return result
        else:
            logger.debug("Could not find one of the sides in the relationship")


class MarriedNormalizer(object):

    def normalize(self, span=None, result=None):
        logger.debug("Postprocessing result for [%s] and [%s]", span, result)
        match = spacy_utils.find_element(span=span, start_at=span.start, mode="forward", attr_key="text",
                                         attr_val=result, max_tokens=100)
        if not match:
            logger.debug("Could not find match for: %s", result)
            return None

        found = spacy_utils.find_elements(span=span, start_at=match.i, mode="backward", attr_key="is_person_part",
                                          attr_val=True, max_tokens=10, ext=True)

        entries = set()
        for token in found:
            entries.add(token._.get_person)

        if len(entries) != 2:
            print("Found invalid number of persons before token married:", entries)
            return None

        entries = list(entries)
        rel_mapping = rel_map[result.strip().lower()]
        template = "{0}:{1}"
        left = template.format(entries[0].start_char, entries[0].end_char)
        right = template.format(entries[1].start_char, entries[1].end_char)
        result = "[{0}],{1},[{2}]".format(left, rel_mapping, right)
        return result
