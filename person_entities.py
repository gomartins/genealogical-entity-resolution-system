import logging
import uuid
from collections import defaultdict
from operator import attrgetter
from operator import itemgetter
from constants import *
from utils import Utils

logger = logging.getLogger('logger')
config = ConfigHandler()

GROUP_ATTRIBUTE_MATCH_SCORE = 1
GROUP_ATTRIBUTE_MISMATCH_PENALTY = -5

PROP_SIMILARITY_WEIGHTS = {
    PERSON_FIRST_NAME: 10,
    PERSON_MIDDLE_NAMES: 4,
    PERSON_LAST_NAME: 2,
    PERSON_NICKNAME: 6,
    PERSON_LAST_NAME_PRIOR_WEDDING: 6,
    PERSON_GEN_TITLE: 4,
    PERSON_ROYAL_TITLE: 4,
    PERSON_GENDER: 4,
}


class SimilarityCalculator(object):

    @staticmethod
    def similarity(person1, person2):
        score = 0
        for prop in PROP_SIMILARITY_WEIGHTS:
            p1 = getattr(person1, prop)
            p2 = getattr(person2, prop)
            if p1 and p2:
                score += SimilarityCalculator.__similarity(p1, p2, prop)

        score = score / len(PROP_SIMILARITY_WEIGHTS)
        return score

    @staticmethod
    def __similarity(p1, p2, prop):
        score = 0
        logger.debug("Comparing property [%s]: [%s] and [%s]", prop, p1, p2)
        if p1 and isinstance(p1, list) and p2 and isinstance(p2, list):
            if any(i in p1 for i in p2):
                score += 1 * PROP_SIMILARITY_WEIGHTS[prop]
        elif str(p1).strip().lower() == str(p2).strip().lower():
            match_score_value = float(config.get('GROUP_ATTRIBUTE_MATCH_SCORE'))
            logger.debug("Properties are the same: [%s] and [%s]", p1, p2)
            score += match_score_value * PROP_SIMILARITY_WEIGHTS[prop]
        else:
            penalty = float(config.get('GROUP_ATTRIBUTE_MISMATCH_PENALTY'))
            score += penalty * PROP_SIMILARITY_WEIGHTS[prop]
        return score


class PersonReference(object):

    def __init__(self, **kwargs):

        # Sets the following properties to this instance dynamically
        keys = ['rel', PERSON_FULL_NAME, PERSON_FIRST_NAME, PERSON_LAST_NAME, PERSON_LAST_NAME_PRIOR_WEDDING,
                PERSON_MIDDLE_NAMES, PERSON_GENDER, PERSON_GEN_TITLE, PERSON_ROYAL_TITLE, PERSON_NICKNAME,
                PERSON_COURTESY_TITLE, PERSON_ARMY_TITLE, PERSON_ARMY_RELATED, PERSON_OTHER_TITLE,
                'pronoun', PERSON_DOB, PERSON_MOB, PERSON_YOB, PERSON_DOD, PERSON_MOD, PERSON_YOD,
                'span', 'document_id']
        for key in keys:
            setattr(self, key, kwargs.get(key))

        if self.span:
            self.start = self.span.start
            self.end = self.span.end
            self.char_start = self.span.start_char
            self.char_end = self.span.end_char
        self.wiki = None
        self.unique_group_id = None
        # Used after rel is mapped into groups
        self.mapped_rel = []

    def get_rels(self):
        return self.rel

    def is_pronoun(self):
        return self.pronoun is not None

    def is_offset_before(self, person):
        if self.start > person.start or self.end > person.end:
            return False
        return True

    def get_name_attrs(self):
        attrs_other = []
        attrs_other.extend(list(attrgetter(PERSON_FIRST_NAME, PERSON_LAST_NAME, PERSON_NICKNAME,
                                           PERSON_GEN_TITLE)(self)))
        middle_names = attrgetter(PERSON_MIDDLE_NAMES)(self)
        if middle_names:
            attrs_other.extend(list(middle_names))
        attrs_other = list(filter(None, attrs_other))
        return attrs_other

    def is_same(self, person):

        same_first_name = Utils.is_str_equals_ignore_case(person.first_name, self.first_name)
        same_last_name = Utils.is_str_equals_ignore_case(person.last_name, self.last_name)
        same_gen_title = Utils.is_str_empty_or_equals_ignore_case(person.generational_title, self.generational_title)

        if same_first_name and same_last_name and same_gen_title:
            logger.info("Names match for %s and %s", self, person)
            return True

        # Same date of birth and a common name
        if (person.yob and person.yob == self.yob
                and person.mob and person.mob == self.mob
                and person.dob and person.dob == self.dob
                and any(item in person.get_name_attrs() for item in self.get_name_attrs())):
            logger.info("Dates of birth match for %s and %s", self, person)
            return True

        return False

    def get_props(self):
        props = [self.first_name, self.last_name, self.generational_title, self.nickname, self.gender, self.yob,
                 self.mob, self.dob, self.yod]
        if self.middle_names:
            props.extend([name for name in self.middle_names])
        props = list(filter(None, props))
        return props

    def get_similarity(self, person):
        if self.is_same(person):
            return 1000.0
        return SimilarityCalculator.similarity(self, person)

    def get_identification(self):
        return "{0} [{1}:{2}]".format(self.full_name, self.start, self.end)

    def to_dict(self):
        return {
            'id': self.get_identification(),
            'original': self.full_name,
            PERSON_FIRST_NAME: self.first_name,
            PERSON_MIDDLE_NAMES: self.middle_names,
            PERSON_LAST_NAME: self.last_name,
            PERSON_ROYAL_TITLE: self.royal_title,
            PERSON_GEN_TITLE: self.generational_title,
            PERSON_NICKNAME: self.nickname,
            PERSON_GENDER: self.gender,
            PERSON_DOB: self.dob,
            PERSON_MOB: self.mob,
            PERSON_YOB: self.yob,
            PERSON_DOD: self.dod,
            PERSON_MOD: self.mod,
            PERSON_YOD: self.yod,
            'start': self.start,
            'group_id': self.unique_group_id
        }

    def __eq__(self, other):
        if not isinstance(other, PersonReference):
            return NotImplemented
        return self.is_same(other)

    def __hash__(self):
        return hash(self.full_name)

    def __repr__(self):
        if not self.middle_names:
            self.middle_names = []
        if self.pronoun:
            return "{0} <{1}> ({2}-{3})".format(self.pronoun, self.gender, self.start, self.end)
        return "{0} {1} {2} {3} {4} <{5}> ({6}-{7}) ({8}-{9})" \
            .format(self.first_name or "",
                    " ".join(self.middle_names) or "",
                    self.last_name or "",
                    self.generational_title or "",
                    self.nickname or "",
                    self.gender or "?",
                    self.yob or "0000",
                    self.yod or "0000",
                    self.start,
                    self.end)


class PersonGroup(object):

    def __init__(self, group_id):
        self.first_occurrence_index = 99999999999999
        self.persons = []
        self.pronouns = []
        self.id = group_id
        self.unique_id = uuid.uuid4()
        self.person_index = {}

    def get_person(self, char_start, char_end):
        key = (char_start, char_end)
        return self.person_index[key] if key in self.person_index else None

    def add_person(self, person):
        self.person_index[(person.char_start, person.char_end)] = person
        if person.start < self.first_occurrence_index:
            self.first_occurrence_index = person.start
        person.unique_group_id = self.unique_id
        self.persons.append(person)

    def add_group_persons(self, group):
        for person in group:
            self.add_person(person)

    def add_pronoun(self, pronoun):
        self.pronouns.append(pronoun)

    def length(self):
        return len(self.persons)

    def get_similarity(self, person):
        similarity = 0.0
        for entry in self.persons:
            similarity += entry.get_similarity(person)
        return similarity / self.length()

    def get_gender(self):
        gender_count = {}
        for person in self.persons:
            if person.gender:
                if person.gender not in gender_count:
                    gender_count[person.gender] = 1
                else:
                    gender_count[person.gender] = gender_count[person.gender] + 1
        if gender_count:
            return max(gender_count.items(), key=itemgetter(1))[0]

    def get_merged_name(self):
        first_name = self.get_attribute(PERSON_FIRST_NAME)
        last_name = self.get_attribute(PERSON_LAST_NAME)
        return f"{first_name} {last_name} ({self.unique_id})"

    def get_consolidated_person(self, prefix=""):
        last_name = self.get_attribute(PERSON_LAST_NAME)
        first_name = self.get_attribute(PERSON_FIRST_NAME, exclude_value=last_name)
        data = {
            prefix + 'group_id': str(self.unique_id),
            prefix + 'merged_name': self.get_merged_name(),
            prefix + PERSON_FIRST_NAME: first_name,
            prefix + PERSON_MIDDLE_NAMES: self.get_attribute(PERSON_MIDDLE_NAMES),
            prefix + PERSON_LAST_NAME: last_name,
            prefix + PERSON_LAST_NAME_PRIOR_WEDDING: self.get_attribute(PERSON_LAST_NAME_PRIOR_WEDDING),
            prefix + PERSON_NICKNAME: self.get_attribute(PERSON_NICKNAME),
            prefix + PERSON_GENDER: self.get_attribute(PERSON_GENDER),
            prefix + PERSON_DOB: self.get_attribute(PERSON_DOB),
            prefix + PERSON_MOB: self.get_attribute(PERSON_MOB),
            prefix + PERSON_YOB: self.get_attribute(PERSON_YOB),
            prefix + PERSON_DOD: self.get_attribute(PERSON_DOD),
            prefix + PERSON_MOD: self.get_attribute(PERSON_MOD),
            prefix + PERSON_YOD: self.get_attribute(PERSON_YOD),
            prefix + PERSON_GEN_TITLE: self.get_attribute(PERSON_GEN_TITLE),
            prefix + PERSON_ROYAL_TITLE: self.get_attribute(PERSON_ROYAL_TITLE)
        }
        flattened_relationships = defaultdict(list)
        # iterates over all relationships to make it available in the final dictionary
        # example: mother_first_name, mother_last_name, etc
        if not prefix:  # prevents endless recursion
            all_relationships = []
            relationships = self.__get_mapped_relationships()
            for rel_id in relationships:
                if isinstance(relationships[rel_id], list):
                    for rel in relationships[rel_id]:
                        props = rel.get_consolidated_person(rel_id + "_")
                        all_relationships.append(props)
                else:
                    props = relationships[rel_id].get_consolidated_person(rel_id + "_")
                    all_relationships.append(props)
            for d in all_relationships:  # you can list as many input dicts as you want here
                for key, value in d.items():
                    flattened_relationships[key].append(value)
        logger.debug("Flattened relationships for %s: %s", self.get_merged_name(), flattened_relationships)
        return {**data, **flattened_relationships}

    def __get_mapped_relationships(self):
        """This is only available after the map relationships method is called"""
        rels = {}
        for person in self.persons:
            for rel in person.mapped_rel:
                logger.debug("Getting relationships for %s: %s", person, rel)
                rels[rel['predicate']] = rel['object']
        return rels

    def get_wiki(self):
        return self.get_attribute('wiki')

    def get_attribute(self, attr, exclude_value=None):
        if exclude_value:
            values = [getattr(person, attr) for person in self.persons if getattr(person, attr) != exclude_value]
            return Utils.most_frequent(list(filter(None, values)))
        values = [getattr(person, attr) for person in self.persons]
        if attr == PERSON_MIDDLE_NAMES:
            # Joined values
            values = [" ".join(e) for e in values if e]
        return Utils.most_frequent(list(filter(None, values)))

    def get_all_tokens(self):
        tokens = [self.get_attribute(PERSON_FIRST_NAME)]
        for person in self.persons:
            if person.middle_names:
                for name in person.middle_names:
                    tokens.append(name)
        tokens.append(self.get_attribute(PERSON_LAST_NAME))
        tokens.append(self.get_attribute(PERSON_NICKNAME))
        tokens.append(self.get_attribute(PERSON_GEN_TITLE))
        tokens.append(self.get_attribute(PERSON_ROYAL_TITLE))
        tokens = list(set(filter(None, tokens)))
        return " ".join(tokens)

    def __repr__(self):
        return "{0} ({1})".format(self.get_merged_name(), len(self.persons))

    def __iter__(self):
        return iter(self.persons)

