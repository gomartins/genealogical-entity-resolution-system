import logging
import uuid
from constants import *
from spacy_utils import SpacyUtils

logger = logging.getLogger('logger')
config = ConfigHandler()
utils = SpacyUtils()


class PersonResolution(object):

    def __init__(self, person_references):
        self.person_references = person_references
        self.unique_res_id = uuid.uuid4()
        self.groups = []
        self.person_tracking = set()
        self.group_tracking = {}  # using a dictionary so there is no need to iterate over the set

    def next_id(self):
        return len(self.groups) + 1

    def person_exists(self, person):
        return person.get_identification() in self.person_tracking

    def add(self, group):
        for person in group:
            self.person_tracking.add(person.get_identification())
        self.groups.append(group)
        self.group_tracking[str(group.unique_id)] = group

    def find_group_by_offset(self, char_start, char_end):
        for group in self.groups:
            person = group.get_person(char_start, char_end)
            logger.debug("Find person by offset (%s,%s) in group %s: %s", char_start, char_end, group, person)
            if person:
                return group

    def get_previous_occurrences(self, span):
        occurrences = [group for group in self.groups if group.first_occurrence_index < span.start]
        return occurrences

    def find_people_within_sentences(self, sentences, gender, before_index):
        groups = []
        for group in self.groups:
            for person in group:
                for sent in sentences:
                    if person.start >= sent.start and person.end <= before_index and person.gender == gender:
                        groups.append(group)
                        break
        return list(set(groups))

    def find_pronoun_group(self, person):
        pronoun = person.span

        prev_token = utils.get_prev_token(pronoun)
        if utils.is_person_token(prev_token) and str(pronoun).lower() in ['himself', 'herself']:
            token_to_span = prev_token.doc[prev_token.i:prev_token.i + 1]
            group = self.find_group_by_offset(token_to_span.start_char, token_to_span.end_char)
            if group:
                return group

        bef_prev_token = utils.get_prev_token(prev_token)
        if str(prev_token).lower() == TOKEN_AND and utils.is_person_token(bef_prev_token):
            token_to_span = bef_prev_token.doc[bef_prev_token.i:bef_prev_token.i + 1]
            group = self.find_group_by_offset(token_to_span.start_char, token_to_span.end_char)
            if group:
                return group

        groups_found = self.get_previous_occurrences(pronoun)
        logger.debug("Finding a total of %s groups for pronoun %s: %s", len(groups_found), pronoun, groups_found)
        if len(groups_found) == 1:
            logger.debug("Returning group %s for pronoun %s", groups_found[0], pronoun)
            return groups_found[0]
        gender = person.gender
        filtered = [entry for entry in groups_found if entry.get_gender() == gender]
        logger.debug("Finding a total of %s groups for pronoun %s and gender %s: %s", len(filtered), pronoun, gender,
                     filtered)
        if len(filtered) == 1:
            return filtered[0]
        elif len(filtered) > 1:
            previous_sentence = pronoun.doc[pronoun.sent.start - 1].sent
            current_sentence = pronoun.sent
            sentences = [previous_sentence, current_sentence]
            groups_found = self.find_people_within_sentences(sentences, gender, pronoun.start)
            if groups_found:
                # sort first by length, then order of appearance (higher/later comer first)
                sorted_group = sorted(groups_found, key=lambda k: (k.length(), k.first_occurrence_index), reverse=True)
                return sorted_group[0]
            filtered.sort(key=lambda x: x.length(), reverse=True)
            return filtered[0]

    def __filter_groups_by_occurrence_index(self, groups, start_index):
        return [group for group in groups if group.first_occurrence_index < start_index]

    def find_person_group_by_first_and_last_name(self, target_person):
        groups_found = []
        for group in self.groups:
            for person in group:
                if (person.first_name and person.last_name
                        and person.first_name.lower() == target_person.first_name.lower()
                        and (person.last_name.lower() == target_person.last_name.lower())
                        and person.generational_title == target_person.generational_title):
                    groups_found.append(group)
                    break
        if len(groups_found) > 1:
            groups_found = self.__filter_groups_by_occurrence_index(groups_found, target_person.start)
        return groups_found

    def find_person_group_by_last_name(self, target_person):
        groups_found = []
        for group in self.groups:
            for person in group:
                if (person.last_name
                        and person.last_name.lower() == target_person.last_name.lower()
                        and person.generational_title == target_person.generational_title):
                    groups_found.append(group)
                    break
        if len(groups_found) > 1:
            groups_found = self.__filter_groups_by_occurrence_index(groups_found, target_person.start)
        return groups_found

    def find_person_group(self, person):
        logger.debug("Looking for person group for %s", person)
        if person.is_pronoun():
            logger.debug("Person is actually a pronoun! Searching for pronoun group.")
            return self.find_pronoun_group(person)

        if person.first_name and person.last_name:
            groups_found = self.find_person_group_by_first_and_last_name(person)
            if len(groups_found) == 1:
                logger.debug("First and last name match. Person %s with group %s", person, groups_found[0])
                return groups_found[0]

        if not person.first_name and person.last_name:
            groups_found = self.find_person_group_by_last_name(person)
            if len(groups_found) == 1:
                logger.debug("Found single group with same last name. Person %s, group %s", person, groups_found[0])
                return groups_found[0]
            elif len(groups_found) > 1:
                # Sorts by group length
                selected = sorted(groups_found, key=lambda x: len(x.persons), reverse=True)[0]
                logger.debug("Found multiple groups with same last name. Returning the most significant", person, selected)
                return selected

        plausible_groups = self.get_plausible_groups(person)

        max_similarity = 0
        current_group = None
        for group in plausible_groups:
            sim = group.get_similarity(person)
            if sim > max_similarity:
                max_similarity = sim
                current_group = group
            logger.debug("Calculated similarity for person %s with group %s: %s", person, group, sim)
        logger.debug("Max. similarity for person %s with group %s: %s", person, current_group, max_similarity)
        if max_similarity > float(config.get('GROUP_SIMILARITY_THRESHOLD')):
            return current_group

    def get_plausible_groups(self, person_target):
        """This returns only the person groups where the person target is not contained
        as part of a relationship object. For example:
        Person Target: Michelle Obama
        Group: Barack Obama (which married to Michelle Obama)
        So Michelle Obama cannot be of this group of person references!
        """
        groups = []
        for group in self.groups:
            plausible = True
            for person in group:
                # If no relationships, group
                if not person.rel:
                    continue
                rel_objects = self.get_relationship_object(person.rel)
                # If the person target is contained a relationship object, then this group is not plausible
                if person_target in rel_objects:
                    plausible = False
                    break
            if plausible:
                groups.append(group)
        return groups

    def get_relationship_object(self, relationship):
        rel_objects = []
        rel_list = None
        if isinstance(relationship, list):
            rel_list = relationship
        else:
            rel_list = [relationship]
        for rel in rel_list:
            offset = rel.split(",")[2][1:-1].split(":")
            start = int(offset[0])
            end = int(offset[1])
            rel_object = [e for e in self.person_references if e.char_start == start and e.char_end == end]
            if rel_object:
                rel_objects.append(rel_object[0])
        return rel_objects

    def find_group_by_id(self, group_id):
        return self.group_tracking[group_id]

    def get_consolidated_persons(self):
        consolidated_persons = []
        for group in self.groups:
            consolidated = group.get_consolidated_person()
            consolidated['res_and_group_id'] = str(self.unique_res_id) + "_" + consolidated['group_id']
            consolidated_persons.append(consolidated)
        return consolidated_persons

    def __repr__(self):
        return '\n'.join(str(v) for v in self.groups)

    def __iter__(self):
        return iter(self.groups)
