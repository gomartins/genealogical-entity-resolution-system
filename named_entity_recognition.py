import logging
import unidecode
import re
import ast
from spacy_utils import SpacyUtils
from constants import *

config = ConfigHandler()

# The following define how many tokens we look around a name
# This helps to address cases where the full name is not recognised
MAX_TOKENS_FORWARD = int(config.get('PERSON_RECOGNITION_FORWARD_TOKENS'))
MAX_TOKENS_BACK = int(config.get('PERSON_RECOGNITION_BACKWARD_TOKENS'))

ARMY_TITLES = ast.literal_eval(config.get('ARMY_TITLES'))
ROYAL_TITLES = ast.literal_eval(config.get('ROYAL_TITLES'))

# "née" is used to identify a woman by her maiden family name.
# The text below has no accents for normalization purposes.
FORMERLY_CALLED = 'nee'


SPACY_POS_TAG_PROP = "tag_"
SPACY_POS_PROPER_NOUN = "NNP"
SPACY_POS_PRONOUN = 'PRON'
SPACY_POS_PARTICLE = 'PART'


utils = SpacyUtils()
logger = logging.getLogger('logger')


class PersonRecognition(object):
    """
    This class identifies Person Entities in a given (spacy) document and creates a named span and token extensions
    """

    def __init__(self, document_id=None, exclusion_map=None):
        self.document_id = document_id
        self.exclusion_map = exclusion_map

    def get_person_spans(self, document):
        person_name_spans = []
        people_offsets = self.__get_people_offset(document)
        for span in people_offsets:
            person_name_spans.append(span)
        return person_name_spans

    def __get_people_offset(self, document):
        people_offsets = []
        entities = (entity for entity in document.ents if entity.label_ == 'PERSON')
        for entity in entities:

            # Baseline has all the following commented out

            has_particle = self.__has_particle(entity)  # I1
            entity = self.__normalize_malformed(document, entity)  # I2
            entity = self.__normalize_particle(document, entity)  # I3
            entity = self.__normalize_quotes(document, entity)  # I2
            if not has_particle:  # I1
                entity = self.__expand_applicable_names(document, entity)  # I1
            entity = self.__remove_ending_comma(document, entity)  # I2

            if self.__is_court_case(entity):  # I2
                logger.debug("Skipping potential court case: %s", entity)
                continue

            if self.__is_enclosed_by_double_quotes(entity):  # I3
                logger.debug("Skipping name enclosed by double quotes: %s", str(entity))
                continue

            if self.__is_preceded_by_nee(entity):  # I2
                logger.debug("Skipping entity identified after 'née': %s", entity)
                continue

            if self.__is_preceded_by_article_the(entity):  # I1
                continue

            if self.__has_particle_and_disease(entity):  # I2
                continue

            if self.__exists_in_offset(entity, people_offsets) or self.__is_excluded(entity):  # I1
                continue

            people_offsets.append(entity)

        self.__set_pronouns_offsets(document, people_offsets)

        people_offsets.sort(key=lambda span: span.start)
        return people_offsets

    @staticmethod
    def __remove_ending_comma(document, entity):
        if str(entity[-1]).lower() == TOKEN_COMMA:
            entity = document[entity.start:entity.end - 1]
        return entity

    def __expand_applicable_names(self, document, entity):
        ppn = self.__get_names(entity.sent, entity.end, "forward", MAX_TOKENS_FORWARD)
        if ppn:
            lower = str(ppn[-1]).lower()
            if lower not in [TOKEN_AND, TOKEN_DOT, TOKEN_COMMA]:
                entity = document[entity.start:ppn[-1].i + 1]
            if lower == TOKEN_DOT and str(document[entity.start:entity.end][-1]).lower() in ['sr', 'jr']:
                entity = document[entity.start:ppn[-1].i + 1]
        return entity

    @staticmethod
    def __has_particle(entity):
        return entity[-1].pos_ == SPACY_POS_PARTICLE

    @staticmethod
    def __normalize_particle(document, entity):
        if PersonRecognition.__has_particle(entity):
            entity = document[entity.start:entity.end - 1]
        return entity

    @staticmethod
    def __normalize_malformed(document, entity):
        if re.search("\\.\\[", str(entity)):
            logger.debug("Entity is malformed: %s", entity)
            entity = document[entity.start:entity.end - 1]
        return entity

    @staticmethod
    def __normalize_quotes(document, entity):
        if str(entity).count(TOKEN_DB_QUOTES) == 1:
            if str(utils.get_next_token(entity)) == TOKEN_DB_QUOTES:
                entity = document[entity.start:entity.end + 1]
            if str(utils.get_prev_token(entity)) == TOKEN_DB_QUOTES:
                entity = document[entity.start - 1:entity.end]
        return entity

    @staticmethod
    def __is_court_case(entity):
        prev_token = utils.get_prev_token(entity)
        next_token = utils.get_next_token(entity)
        if str(prev_token) == 'v.' or str(next_token) == 'v.':
            return True
        return False

    @staticmethod
    def __is_enclosed_by_double_quotes(entity):
        prev_token = utils.get_prev_token(entity)
        next_token = utils.get_next_token(entity)
        if prev_token and next_token and str(prev_token) == TOKEN_DB_QUOTES and str(next_token) == TOKEN_DB_QUOTES:
            return True
        return False

    @staticmethod
    def __is_preceded_by_nee(entity):
        prev_token = utils.get_prev_token(entity)
        if prev_token and FORMERLY_CALLED == unidecode.unidecode(str(prev_token).lower().strip()):
            return True
        return False

    @staticmethod
    def __is_preceded_by_article_the(entity):
        if entity.start > 0 and entity.doc[entity.start - 1].lower_ == TOKEN_THE:
            return True
        return False

    @staticmethod
    def __has_particle_and_disease(entity):
        next_token = utils.get_next_token(entity)
        if next_token and next_token.pos_ == SPACY_POS_PARTICLE:
            next_token = utils.get_next_token(next_token)
            if next_token and str(next_token).lower() == 'disease':
                return True
        return False

    def __is_excluded(self, span):
        if self.exclusion_map and self.document_id:
            found_person_range = (span.start_char, span.end_char)
            exclusions = self.exclusion_map.get(self.document_id)
            if exclusions and found_person_range in exclusions:
                return True
        return False

    # Prevent entries such as Algernon Edward Urban Sartoris to become:
    # 1 - Algernon Edward Urban Sartoris
    # 2 - Urban Sartoris
    @staticmethod
    def __exists_in_offset(person_span, people_offsets):
        for offset in people_offsets:
            if offset.start <= person_span.start and offset.end >= person_span.end:
                return True
        return False

    def __set_pronouns_offsets(self, document, people_offsets):
        for token in document:
            token_span = document[token.i:token.i+1]
            if token.pos_ == SPACY_POS_PRONOUN and token.lower_ in PRONOUNS:
                if self.__is_excluded(token_span):
                    continue
                people_offsets.append(document[token.i:token.i + 1])

    @staticmethod
    def __get_names(sentence, start_at, direction, max_tokens):
        exclude_ents = ['DATE', 'CARDINAL']
        return utils.find_elements_sequence(sentence, start_at, direction, SPACY_POS_TAG_PROP, SPACY_POS_PROPER_NOUN, max_tokens=max_tokens, exclude_ent_types=exclude_ents)




