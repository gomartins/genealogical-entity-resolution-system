import collections
import copy
import json

import scores
from constants import ConfigHandler, PRONOUNS, GENDER_MALE, GENDER_FEMALE, BASE_DIRECTORY
from graph_database import Database
from name_handler import PronounHandler
from utils import *

logger = logging.getLogger('logger')
pronoun_handler = PronounHandler()
config = ConfigHandler()
USE_EXCLUSION_MAP = True

GENERATIONAL_TITLES = config.get('generational_titles')


class ValidationReference(object):

    def __init__(self, char_start, char_end, text, pronoun, source_document):
        self.char_start = char_start
        self.char_end = char_end
        self.text = text
        self.pronoun = pronoun
        self.source_document = source_document

    def __repr__(self):
        return "{0}: [{1} [{2},{3}]]".format(self.text, self.source_document, self.char_start, self.char_end)


class ValidationHelper(object):

    def __init__(self, file_list):
        self.validation_map = self.load_validation(file_list)

    def load_data_mapping(self):
        annotation_map = {}
        with open(BASE_DIRECTORY + "annotated_wikipedia_articles.jsonl", 'r', encoding="UTF-8") as file:
            lines = file.readlines()
            for line in lines:
                data = json.loads(line)
                source_file = data['src']
                if source_file in annotation_map:
                    print("File already exists in annotated document (all.jsonl). Is it duplicate?!", source_file)
                annotation_map[data['src']] = data
        return annotation_map

    def load_validation(self, file_list):
        data_map = self.load_data_mapping()
        validation_map = {}
        for file_name in file_list:
            data = data_map[file_name]
            document_text = data['text'].strip()
            labels = data['label']
            for entry in labels:
                start = entry[0]
                end = entry[1]
                entity = entry[2]
                text = document_text[start:end]
                if "GROUP" in entity or "Group" in entity or "TEMPORARY" in entity:
                    pos = "{:.2f}%".format(start / len(document_text) * 100)
                    text_fmt = "Invalid annotation found in {0}: {1} -> {2}. Location: {3}".format(file_name, text,
                                                                                                   entity, pos)
                    print(text_fmt)
                # Checks if starts or ends with space
                # Or if is not a gen. title and ends with dot (mistakenly selected).
                if text.startswith(' ') or text.endswith(' ') \
                        or (text.split(" ")[-1].replace(".", "").lower() not in GENERATIONAL_TITLES
                            and text.endswith(".")):
                    log_entry = "Extra space or dot for text '{0}' [{1}:{2}] - Entity: {3} - Doc: {4}" \
                        .format(text, start, end, entity, file_name)
                    logger.debug(log_entry)
                is_pronoun = text.lower() in PRONOUNS
                reference = ValidationReference(start, end, text, is_pronoun, file_name)
                if entity in validation_map:
                    validation_map[entity].append(reference)
                else:
                    validation_map[entity] = [reference]
        return validation_map

    def get_exclusion_map(self):
        if 'Unknown' not in self.validation_map:
            return {}
        exclusion_map = {}
        for entry in self.validation_map['Unknown']:
            doc_id = entry.source_document
            map_entry = None
            if doc_id in exclusion_map:
                map_entry = exclusion_map[doc_id]
            else:
                map_entry = []
                exclusion_map[doc_id] = map_entry
            map_entry.append((entry.char_start, entry.char_end))
        return exclusion_map

    def __get_key_tokens(self, key):
        tokens = []
        for entry in self.validation_map[key]:
            tokens.extend(entry.text.split())
        # remove pronouns
        tokens = [token for token in tokens if not pronoun_handler.is_pronoun(token)]
        return tokens

    # This is a effort to find the appropriate group based on a set of tokens
    # At the moment I couldn't find a different way of validating the results
    def __find_group_by_tokens(self, groups, consumed_groups, tokens):
        sim = 0
        found = None
        for group in groups:
            if group in consumed_groups:
                # We need to skip groups that were already assigned to an entity, otherwise they are used again
                continue
            g_tokens = group.get_all_tokens().split()
            current_sim = Utils.jaccard_similarity(tokens, g_tokens)
            if current_sim > sim:
                sim = current_sim
                found = group
        logger.debug("Group [%s] found for tokens %s with score: %s", found, tokens, sim)
        return found

    def __find_group_by_offsets(self, entity_id, groups, consumed_groups):
        sim = 0
        # Basically gets all ranges from the entity
        # Michelle_Obama_0:13, Michelle_Obama_22:32, etc
        annotated_ranges = set([e.source_document + "_" + str(e.char_start) + ":" + str(e.char_end) for e in
                                self.validation_map[entity_id]])
        found = None
        for group in groups:
            if group in consumed_groups:
                # We need to skip groups that were already assigned to an entity, otherwise they are used again
                continue
            group_ranges = set([e.document_id + "_" + str(e.char_start) + ":" + str(e.char_end) for e in group])
            intersect = annotated_ranges.intersection(group_ranges)
            if len(intersect) == 0:
                continue
            current_sim = len(intersect) / len(annotated_ranges)
            if current_sim > sim:
                sim = current_sim
                found = group
        logger.debug("Group [%s] found using ranges with score: %s", found, sim)
        return found

    def __find_group(self, entity_id, groups, consumed_groups):
        group = self.__find_group_by_offsets(entity_id, groups, consumed_groups)
        if not group:
            annotated_person_tokens = self.__get_key_tokens(entity_id)  # get tokens from manually annotated docs
            logger.debug("Tokens found from key %s: %s", entity_id, annotated_person_tokens)
            group = self.__find_group_by_tokens(groups, consumed_groups, annotated_person_tokens)
        logger.debug("Group found for %s: %s", entity_id, group)
        return group

    def get_scores(self, groups):

        ground_truth_all = self.__get_ground_truth_clusters('all')
        res_data_all = self.__get_resolution_clusters(groups, 'all')
        muc_all = scores.muc(ground_truth_all, res_data_all)
        b3_all = scores.b_cubed(ground_truth_all, res_data_all)
        ceaf_e_all = scores.ceaf_e(ground_truth_all, res_data_all)
        ceaf_m_all = scores.ceaf_m(ground_truth_all, res_data_all)
        avg_all = scores.conll2012(ground_truth_all, res_data_all)

        ground_truth_pronouns = self.__get_ground_truth_clusters('pronouns')
        res_data_pronouns = self.__get_resolution_clusters(groups, 'pronouns')
        muc_pronouns = scores.muc(ground_truth_pronouns, res_data_pronouns)
        b3_pronouns = scores.b_cubed(ground_truth_pronouns, res_data_pronouns)
        ceaf_e_pronouns = scores.ceaf_e(ground_truth_pronouns, res_data_pronouns)
        ceaf_m_pronouns = scores.ceaf_m(ground_truth_pronouns, res_data_pronouns)
        avg_pronouns = scores.conll2012(ground_truth_pronouns, res_data_pronouns)

        ground_truth_persons = self.__get_ground_truth_clusters('persons')
        res_data_persons = self.__get_resolution_clusters(groups, 'persons')
        muc_persons = scores.muc(ground_truth_persons, res_data_persons)
        b3_persons = scores.b_cubed(ground_truth_persons, res_data_persons)
        ceaf_e_persons = scores.ceaf_e(ground_truth_persons, res_data_persons)
        ceaf_m_persons = scores.ceaf_m(ground_truth_persons, res_data_persons)
        avg_persons = scores.conll2012(ground_truth_persons, res_data_persons)

        results = {
            'all': {'muc': muc_all, 'b3': b3_all, 'ceaf_e': ceaf_e_all, 'ceaf_m': ceaf_m_all, 'avg': avg_all},
            'persons': {'muc': muc_persons, 'b3': b3_persons, 'ceaf_e': ceaf_e_persons, 'ceaf_m': ceaf_m_persons,
                        'avg': avg_persons},
            'pronouns': {'muc': muc_pronouns, 'b3': b3_pronouns, 'ceaf_e': ceaf_e_pronouns, 'ceaf_m': ceaf_m_pronouns,
                         'avg': avg_pronouns}
        }
        return results

    def get_reference_map(self, remove_unknown=False):
        ref_map = {}
        annotated_map = copy.deepcopy(self.validation_map)
        if remove_unknown:
            annotated_map.pop('Unknown')
        for reference in [x for v in annotated_map.values() for x in v]:
            doc = reference.source_document
            span_range = (reference.char_start, reference.char_end)
            if doc in ref_map:
                ref_map[doc].append(span_range)
            else:
                ref_map[doc] = [span_range]
        return ref_map

    def get_personal_data_score(self, groups):
        db = Database()
        metrics = {
            'found_in_structured_data': 0,
            'not_found_in_structured_data': 0,
            'group_found_in_unstructured_data': 0,
            'group_not_found_in_unstructured_data': 0,
            'structured_data_relationship_not_annotated': 0,
        }

        # Sort by entities having most annotations
        entities = sorted(self.validation_map, key=lambda k: len(self.validation_map[k]), reverse=True)
        all_annotated_ids = set([entry.split("(")[1][:-1] for entry in self.validation_map if '(' in entry])
        consumed_groups = {}

        for entity in entities:
            if entity == 'Unknown':
                continue

            entity_id = entity.split("(")[1][0:-1]
            result = db.get_by_id(entity_id)
            if not result:
                self.__increment_property('not_found_in_structured_data', metrics)
                continue

            self.__increment_property('found_in_structured_data', metrics)
            t_attrs = result.data()['p']

            group = self.__find_group(entity, groups, consumed_groups)
            consumed_groups[group] = entity

            if not group:
                self.__increment_property('group_not_found_in_unstructured_data', metrics)
                print("Group not found for entity", entity_id)
                continue

            r_attrs = group.get_consolidated_person()

            # Gender matching
            GenderMatcher('gender', metrics).compute(t_attrs, r_attrs)

            # First and last name
            FirstNameMatcher('first_name', metrics).compute(t_attrs, r_attrs)
            LastNameMatcher('last_name', metrics).compute(t_attrs, r_attrs)

            # Date of birth parts
            GenericDatePartMatcher('year_of_birth', metrics).compute(t_attrs, 'date_of_birth', 'year', r_attrs, 'yob')
            GenericDatePartMatcher('month_of_birth', metrics).compute(t_attrs, 'date_of_birth', 'month', r_attrs, 'mob')
            GenericDatePartMatcher('day_of_birth', metrics).compute(t_attrs, 'date_of_birth', 'day', r_attrs, 'dob')

            # Date of death parts
            GenericDatePartMatcher('year_of_death', metrics).compute(t_attrs, 'date_of_death', 'year', r_attrs, 'yod')
            GenericDatePartMatcher('month_of_death', metrics).compute(t_attrs, 'date_of_death', 'month', r_attrs, 'mod')
            GenericDatePartMatcher('day_of_death', metrics).compute(t_attrs, 'date_of_death', 'day', r_attrs, 'dod')

            # Date of birth and death unified
            GenericDateMatcher('date_of_birth', metrics).compute(t_attrs, 'date_of_birth', r_attrs, 'yob', 'mob', 'dob')
            GenericDateMatcher('date_of_death', metrics).compute(t_attrs, 'date_of_death', r_attrs, 'yod', 'mod', 'dod')

            aggr_relationships = self.get_aggregated_relationships(db, entity_id)
            for rel_type in aggr_relationships:
                rel_given_attrs = aggr_relationships[rel_type]
                annotated_entries = []
                for entry in rel_given_attrs:
                    wid = entry['id']
                    if wid in all_annotated_ids:
                        annotated_entries.append(entry)
                    else:
                        self.__increment_property('structured_data_relationship_not_annotated', metrics)
                if annotated_entries:
                    RelationshipMatcher(str(rel_type).lower(), metrics).compute(rel_given_attrs, r_attrs)

        all_records = db.get_all()
        all_neo4j_ids = set([e.data()['p']['id'] for e in all_records])

        # This contains common entries between neo4j and annotated records
        common_records_ids = all_neo4j_ids.intersection(all_annotated_ids)
        neo4j_records_not_found_in_annotation = all_neo4j_ids - common_records_ids

        annotated_documents = {x.source_document for v in self.validation_map.values() for x in v}
        annotated_person_references = [x for v in self.validation_map.values() for x in v]
        entities_present_in_multiple_docs = self.get_entities_present_in_multiple_docs()

        print("-----------")
        print("Overall number of person references resolved: ", sum([e.length() for e in groups]))
        print("Number of person (groups) resolved: ", len(groups))
        print("Number of person (groups) used in the validation: ", len(consumed_groups))
        print("Number of annotated documents: ", len(annotated_documents))
        print("Number of annotated person entities: ", len(all_annotated_ids))
        print("Number of annotated person references (including unknown): ", len(annotated_person_references))
        print("Number of annotated unknown person references: ", len(self.validation_map['Unknown']))
        print("Number of annotated persons found in multiple docs.: ", len(entities_present_in_multiple_docs))
        print("Number of Neo4j entries: ", len(all_records))
        print("Number of common records between Neo4J and annotated dataset: ", len(common_records_ids))
        print("Number of Neo4j entries not found in annotations: ", len(neo4j_records_not_found_in_annotation))
        print("-----------")
        print(metrics)
        self.print_metrics(metrics, len(common_records_ids))

    def get_entities_present_in_multiple_docs(self):
        entries = set()
        for entry in self.validation_map:
            annotations = self.validation_map[entry]
            if len(set([e.source_document for e in annotations])) > 1:
                entries.add(entry)
        return entries

    def print_metrics(self, metrics, overall_entries):
        dups = [entry.replace("_non_match", "").replace("_match", "") for entry in metrics]
        filtered = [item for item, count in collections.Counter(dups).items() if count > 1]
        final_metrics = {}
        for prop in filtered:
            matches = metrics.get(prop + "_match")
            non_matches = metrics.get(prop + "_non_match")
            precision = matches / (matches + non_matches)
            recall = matches / overall_entries
            f_score = 0
            if precision != 0 or recall != 0:
                f_score = 2 * (precision * recall) / (precision + recall)
            final_metrics[prop] = "{:.3f}".format(f_score)
            # final_metrics[prop + "_precision"] = "{:.3f}".format(precision)
            # final_metrics[prop + "_recall"] = "{:.3f}".format(recall)
            # final_metrics[prop + "_f_score"] = "{:.3f}".format(f_score)
        print(final_metrics)

    def get_aggregated_relationships(self, db, entity_id):
        relationships = db.get_relationships(entity_id)
        rel_mapping = {}
        for rel in relationships:
            rel_type = rel[0]
            rel_id = rel[1]
            rel_entity = db.get_by_id(rel_id)
            rel_t_attrs = rel_entity.data()['p']
            if rel_type not in rel_mapping:
                rel_entities = [rel_t_attrs]
                rel_mapping[rel_type] = rel_entities
            else:
                rel_mapping[rel_type].append(rel_t_attrs)
        return rel_mapping

    def __increment_property(self, name, data):
        data[name] = data[name] + 1

    def __get_resolution_clusters(self, groups, mode):
        resolution_entries = []
        exclusion_map = self.get_exclusion_map()
        for group in groups:
            entry = set()
            for person in group:
                doc_id = person.document_id
                span_range = (person.char_start, person.char_end)
                if USE_EXCLUSION_MAP and doc_id in exclusion_map and span_range in exclusion_map[doc_id]:
                    print("Person found in exclusion list!!!!!!!!")
                    continue
                if mode == 'pronouns' and not person.pronoun:
                    continue
                if mode == 'persons' and person.pronoun:
                    continue
                text = "{0}_[{1}:{2}]_({3})".format(person.span, person.char_start, person.char_end, person.document_id)
                entry.add(text)
            if entry:
                resolution_entries.append(entry)
        return resolution_entries

    def __get_ground_truth_clusters(self, mode):
        ground_truth = []
        for entity_id in self.validation_map:
            if USE_EXCLUSION_MAP and entity_id == 'Unknown':
                continue
            entry = set()
            for ref in self.validation_map[entity_id]:
                if mode == 'pronouns' and not ref.pronoun:
                    continue
                if mode == 'persons' and ref.pronoun:
                    continue
                text = "{0}_[{1}:{2}]_({3})".format(ref.text, ref.char_start, ref.char_end, ref.source_document)
                entry.add(text)
            if len(entry) > 0:
                ground_truth.append(entry)
        return ground_truth


class BaseMatcher(object):

    def __init__(self, attribute, metrics):
        self.attribute = attribute
        self.metrics = metrics
        self.initialize_props()

    def initialize_props(self):
        match = self.attribute + '_match'
        non_match = self.attribute + '_non_match'
        if match not in self.metrics:
            self.metrics[match] = 0
        if non_match not in self.metrics:
            self.metrics[non_match] = 0

    def increment_property(self, match, override_name=None):
        append_str = "_match" if match else "_non_match"
        if override_name:
            prop_name = override_name + append_str
            if prop_name not in self.metrics:
                self.metrics[prop_name] = 0
        else:
            prop_name = self.attribute + append_str
        self.metrics[prop_name] = self.metrics[prop_name] + 1

    def match_fields(self, res_value, truth_attrs, validate_against_fields, idx):
        for field in validate_against_fields:
            val = truth_attrs.get(field)
            if val:
                truth_value = val.split()[idx]
                if truth_value and res_value and truth_value.lower().strip() == res_value.lower().strip():
                    return True
        return False


class RelationshipMatcher(BaseMatcher):

    def compute(self, rel_truth_attrs_list, res_attrs):
        for rel_truth_attrs in rel_truth_attrs_list:
            rel_type = self.attribute
            max_rels = self.get_number_of_relational_entries(res_attrs, rel_type)
            matches = False
            for idx in range(max_rels):
                relation_attrs = self.get_relational_entry(res_attrs, rel_type, idx)
                if self.person_matches(rel_truth_attrs, relation_attrs):
                    matches = True
                    break

            if matches:
                self.increment_property(True, override_name=rel_type)
            else:
                self.increment_property(False, override_name=rel_type)

    def person_matches(self, truth_attrs, res_attrs):
        validate_against_fields = ['label', 'given_name', 'birth_name', 'known_as']
        r_first_name = res_attrs.get(self.attribute + '_first_name')
        r_last_name = res_attrs.get(self.attribute + '_last_name')

        first_name_matches = self.match_fields(r_first_name, truth_attrs, validate_against_fields, 0)
        last_name_matches = self.match_fields(r_last_name, truth_attrs, validate_against_fields, -1)

        return first_name_matches and last_name_matches

    # Returns the max. number entries in relationship attribute
    # such as "child_of":
    # 'child_of_first_name' ['Marian', 'Fraser']
    # should output 2
    def get_number_of_relational_entries(self, attrs, attr_prefix):
        max_len = 0
        for attr in attrs:
            if attr_prefix in attr:
                attrs_len = len(attrs[attr])
                if attrs_len > max_len:
                    max_len = attrs_len
        return max_len

    def get_relational_entry(self, attrs, attr_prefix, position):
        relational_attrs = {}
        for attr in attrs:
            if attr_prefix in attr:
                attrs_len = len(attrs[attr])
                if position <= (attrs_len - 1):
                    relational_attrs[attr] = attrs[attr][position]
                else:
                    relational_attrs[attr] = None
        return relational_attrs


class GenderMatcher(BaseMatcher):

    def compute(self, truth_attrs, res_attrs):
        attr = self.attribute
        if attr in truth_attrs and attr in res_attrs:
            if truth_attrs[attr] == 'male' and res_attrs[attr] == GENDER_MALE \
                    or truth_attrs[attr] == 'female' and res_attrs[attr] == GENDER_FEMALE:
                self.increment_property(True)
                return
        self.increment_property(False)


class FirstNameMatcher(BaseMatcher):

    def compute(self, truth_attrs, res_attrs):
        validate_against_fields = ['label', 'given_name', 'birth_name', 'known_as']
        r_first_name = res_attrs.get('first_name')
        first_name_matches = self.match_fields(r_first_name, truth_attrs, validate_against_fields, 0)

        if first_name_matches:
            self.increment_property(True)
            return

        self.increment_property(False)


class LastNameMatcher(BaseMatcher):

    def compute(self, truth_attrs, res_attrs):
        validate_against_fields = ['label', 'given_name', 'birth_name', 'known_as', 'family_name']
        r_last_name = res_attrs.get('last_name')
        last_name_matches = self.match_fields(r_last_name, truth_attrs, validate_against_fields, -1)

        if last_name_matches:
            self.increment_property(True)
            return

        self.increment_property(False)


class GenericDateMatcher(BaseMatcher):

    def compute(self, truth_attrs, truth_attr_name, res_attrs, res_attr_year, res_attr_month, res_attr_day):
        t_yob = ValidationDateHandler.get(truth_attrs.get(truth_attr_name), 'year')
        t_mob = ValidationDateHandler.get(truth_attrs.get(truth_attr_name), 'month')
        t_dob = ValidationDateHandler.get(truth_attrs.get(truth_attr_name), 'day')

        r_yob = res_attrs[res_attr_year]
        r_mob = res_attrs[res_attr_month]
        r_dob = res_attrs[res_attr_day]

        if self.is_same(t_yob, r_yob) and self.is_same(t_mob, r_mob) and self.is_same(t_dob, r_dob):
            self.increment_property(True)
        else:
            self.increment_property(False)

    def is_same(self, n1, n2):
        if n1 and n2 and int(n1) == int(n2):
            return True
        elif not n1 and not n2:
            return True
        return False


class GenericDatePartMatcher(BaseMatcher):

    def compute(self, truth_attrs, truth_attr_name, truth_attr_part, res_attrs, res_attr_name):
        date_truth = ValidationDateHandler.get(truth_attrs.get(truth_attr_name), truth_attr_part)
        date_res = res_attrs.get(res_attr_name)

        if date_truth and date_res:
            if int(date_truth) == int(date_res):
                self.increment_property(True)
        elif not date_truth and not date_res:
            self.increment_property(True)
        else:
            self.increment_property(False)


class ValidationDateHandler(object):

    @staticmethod
    def get(date_text, date_type):
        if not date_text:
            return None
        if date_type == 'year':
            return ValidationDateHandler.get_year(date_text)
        if date_type == 'month':
            return ValidationDateHandler.get_month(date_text)
        if date_type == 'day':
            return ValidationDateHandler.get_day(date_text)

    @staticmethod
    def get_day(date_text):
        parts = date_text.split("-")
        if len(parts) == 1 or len(parts) == 2:
            return None

        if len(parts) == 3:
            return parts[2]

    @staticmethod
    def get_month(date_text):
        parts = date_text.split("-")
        if len(parts) == 1:
            return None

        if len(parts) >= 2:
            return parts[1]

    @staticmethod
    def get_year(date_text):
        parts = date_text.split("-")
        if len(parts) == 1:
            # If length is 1, most likely this is a year
            if len(parts[0]) > 4:
                # TODO: This is for scenarios like this: 1815s. Check later
                print("Date with more than 4 digits!", parts[0])
                return parts[0][0:-1]
            return parts[0]
        if len(parts) >= 2:
            if len(parts[0]) == 4 and len(parts[1]) == 4:
                print("Date range encountered!", parts)
            return parts[0]
