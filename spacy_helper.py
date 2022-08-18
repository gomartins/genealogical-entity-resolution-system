import logging

from constants import ConfigHandler, GENDER_MALE, GENDER_FEMALE
from name_handler import NameHandler
from named_entity_recognition import PersonRecognition
from person_entities import PersonGroup, PersonReference
from person_resolution import PersonResolution
from record_linkage import CrossDocumentLinkage, CoreRecordLinkage
from relation_extraction import RelationExtraction
from scrapper import Scrapper
from spacy_utils import SpacyUtils
from utils import Utils

logger = logging.getLogger('logger')
spacy_utils = SpacyUtils()
utils = Utils()
config = ConfigHandler()
name_handler = NameHandler()

NAMED_SPAN_PERSON = config.get('SPACY_NAMED_SPAN_PERSON')


class CrossDocumentResolution(object):

    def __init__(self, nlp, exclusion_map=None):
        self.nlp = nlp
        self.exclusion_map = exclusion_map

    def resolve(self, documents):
        all_consolidated_persons = []
        resolutions = {}
        scrapper = Scrapper()

        texts = []
        for document_name in documents:
            text = scrapper.get_wiki_text(document_name).strip()
            texts.append((text, {'text_id': document_name}))

        logger.error("Starting spaCy's processing for %s documents", len(texts))
        # doc_tuples = self.nlp.pipe(texts, as_tuples=True, disable=["lemmatizer", "textcat"], n_process=1, batch_size=100)
        doc_tuples = self.nlp.pipe(texts, as_tuples=True, disable=["lemmatizer", "textcat"], n_process=4, batch_size=10)
        logger.error("Finished spaCy's processing for %s documents", len(texts))
        for doc, context in doc_tuples:
            text_id = context['text_id']
            logger.error("Starting inner resolution for %s", text_id)
            inner = InnerDocumentResolution(text_id, doc, exclusion_map=self.exclusion_map)
            resolution = inner.resolve_names()
            logger.error("Finished inner resolution for %s", text_id)
            logger.debug("Total person groups in resolution: %s", len(resolution.groups))
            resolutions[str(resolution.unique_res_id)] = resolution
            logger.error("Retrieving consolidated persons for %s", text_id)
            all_consolidated_persons.extend(resolution.get_consolidated_persons())
            logger.error("Finished retrieving consolidated persons for %s", text_id)

        logger.debug("Total number of persons found in all documents: %s", len(all_consolidated_persons))

        logger.error("Started cross resolution")
        linkage = CrossDocumentLinkage()
        groups = linkage.resolve(all_consolidated_persons)
        logger.error("Finished cross resolution")
        logger.debug("Across groups names resolved: %s", groups)

        group_tracking = []
        groups_final, source_target = self.__merge_groups(groups, resolutions, group_tracking)
        for key in resolutions:
            for group in resolutions[key]:
                if str(group.unique_id) not in group_tracking:
                    groups_final.append(group)

        self.__remap_relationships(groups_final, source_target)
        self.__create_reflexive_relationships(groups_final)
        logger.error("Before returning final results")
        return groups_final

    # We iterate over all pairs and add them into the same group
    # (merging people from different docs into the same group)
    def __merge_groups(self, groups, resolutions, group_tracking):
        # this is used to track which was the source group and which is the target after the merging
        group_source_target_mapping = {}
        groups_final = []
        for group in groups:
            pg = PersonGroup(1)
            for res_and_group_id in group:
                parts = res_and_group_id.split("_")
                res_id = parts[0]
                group_id = parts[1]
                original_resolution = resolutions[res_id]
                original_group = original_resolution.find_group_by_id(group_id)
                group_tracking.append(group_id)
                group_source_target_mapping[original_group] = pg
                pg.add_group_persons(original_group)
            groups_final.append(pg)
        return groups_final, group_source_target_mapping

    # This remaps the relationships after the cross-resolution merge.
    # Due to group updates, we need to make sure that relationships point to the updated groups
    def __remap_relationships(self, groups, source_target_mapping):
        for group in groups:
            for person in group:
                invalid_rels = []
                for rel in person.mapped_rel:
                    if rel['subject'] in source_target_mapping:
                        rel['subject'] = source_target_mapping[rel['subject']]
                    if rel['object'] in source_target_mapping:
                        rel['object'] = source_target_mapping[rel['object']]
                    if rel['subject'] == rel['object']:
                        invalid_rels.append(rel)
                person.mapped_rel = [e for e in person.mapped_rel if e not in invalid_rels]

    def __create_reflexive_relationships(self, groups):
        for group in groups:
            for person in group:
                for rel in person.mapped_rel:
                    rel_type = rel['predicate']
                    predicate_mapping = {
                        'sibling_of': 'sibling_of',
                        'spouse_of': 'spouse_of',
                        'father_of': 'child_of',
                        'mother_of': 'child_of',
                        'child_of': 'dynamic',  # Converted into father_of and mother_of dynamically
                    }
                    if 'reflexive' not in rel and rel_type in predicate_mapping:
                        subj_group = rel['subject']
                        obj_group = rel['object']
                        any_person = obj_group.persons[0]
                        mapped_pred = predicate_mapping[rel_type]

                        if mapped_pred == 'dynamic' and subj_group.get_gender() is None:
                            logger.debug("Unable to find gender. Will not create reflexive relationships. %s", person)
                            continue

                        if mapped_pred == 'dynamic' and subj_group.get_gender() == GENDER_FEMALE:
                            mapped_pred = 'mother_of'
                        elif mapped_pred == 'dynamic' and subj_group.get_gender() == GENDER_MALE:
                            mapped_pred = 'father_of'
                        reflex = {'subject': obj_group, 'predicate': mapped_pred, 'object': subj_group,
                                  'reflexive': True}
                        any_person.mapped_rel.append(reflex)


class InnerDocumentResolution(object):

    def __init__(self, document_id, document, exclusion_map=None):
        self.document_id = document_id  # document identifier, eg. Craig_Robinson_(basketball)
        self.document = document
        self.exclusion_map = exclusion_map
        recognition = PersonRecognition(document_id=document_id, exclusion_map=self.exclusion_map)
        person_spans = recognition.get_person_spans(document)
        spacy_utils.initialize_person_entities(document, person_spans)

    def get_person_spans(self):
        return self.document.spans[NAMED_SPAN_PERSON]

    def get_person_references(self):
        references = []
        relation_extraction = RelationExtraction()
        span_relationships = relation_extraction.extract(self.get_person_spans())
        known_names_map = {'first_names': set(), 'last_names': set(), 'nicknames': set()}

        for span in span_relationships:
            attrs = span_relationships[span]
            attrs['document_id'] = self.document_id
            logger.debug("Before creating person with attributes: %s", attrs)
            person_data = name_handler.to_person({span: attrs}, known_names_map=known_names_map)
            person = PersonReference(**person_data)
            references.append(person)
            if person.last_name:
                known_names_map['last_names'].add(person.last_name.lower())
            if person.first_name:
                known_names_map['first_names'].add(person.first_name.lower())
            if person.nickname:
                if isinstance(person.nickname, list):
                    print("Person nickname is list!!!!: ", person.nickname)
                    continue
                known_names_map['nicknames'].add(person.nickname.lower())

        return references

    def resolve_core(self, references):
        core = CoreRecordLinkage()
        person_refs = [s.to_dict() for s in references if s and not s.is_pronoun()]
        core_groups = []
        if len(person_refs) > 1:
            core_groups = core.resolve(person_refs)
        person_map = {p.get_identification(): p for p in references if p and not p.is_pronoun()}
        group_id = 1
        resolution = PersonResolution(references)
        for group in core_groups:
            pg = PersonGroup(group_id)
            for person in group:
                pg.add_person(person_map[person])
            resolution.add(pg)
            group_id += 1
        return resolution

    def resolve_names(self):
        logger.debug("Starting to resolve names")
        all_references = self.get_person_references()

        for per in all_references:
            if per.nee:
                nee = per.nee[0]
                found = [entry for entry in all_references if entry.last_name and entry.last_name == nee]
                if found:
                    print("Found persons with the same last name as the 'née' for %s: %s", per, found)

        resolution = self.resolve_core(all_references)
        group_id = resolution.next_id()
        for person in all_references:
            if resolution.person_exists(person):
                continue
            logger.debug("Trying to find person group for %s", person)
            found = resolution.find_person_group(person)
            if found:
                logger.debug("Found person group: %s [ID: %s]", found, found.id)
                found.add_person(person)
            else:
                logger.debug("Group not found, creating a new one.")
                group = PersonGroup(group_id)
                group.add_person(person)
                resolution.add(group)
                group_id += 1

        self.__map_relationships(resolution)
        self.__sort_groups(resolution)
        return resolution

    def __string_to_offset(self, string):
        parts = string.split(":")
        return int(parts[0][1:]), int(parts[1][:-1])

    def __map_relationships(self, resolution):
        for group in resolution:
            for person in group:
                rels = person.rel
                # [420:428],brother_of,[476:490]
                if rels:
                    logger.debug("Mapping relationship for %s: %s", person, rels)
                    if isinstance(rels, list):
                        mapped_rels = []
                        for rel in rels:
                            result = self.__map_relationship(group, person, rel, resolution)
                            if result and self.__is_relationship_plausible(result):
                                mapped_rels.append(result)
                        person.mapped_rel = mapped_rels
                    else:
                        person.mapped_rel = [self.__map_relationship(group, person, rels, resolution)]
                    # Remove Nones
                    person.mapped_rel = [i for i in person.mapped_rel if i]

    def __is_relationship_plausible(self, relationship):
        # TODO: Not implemented yet
        return True

    def __map_relationship(self, group, person, rels, resolution):
        parts = rels.split(",")
        start, end = self.__string_to_offset(parts[0])
        left_group = resolution.find_group_by_offset(start, end)
        start, end = self.__string_to_offset(parts[2])
        right_group = resolution.find_group_by_offset(start, end)
        # subject must be the same as left and right cannot be the same!
        if left_group == group and right_group != group:
            return {'subject': left_group, 'predicate': parts[1], 'object': right_group}
        else:
            logger.debug("Cannot have a relationship with itself, removing it! Person: %s, Relationships: %s", person,
                         rels)
            return None

    def __sort_groups(self, resolution):
        groups = sorted(resolution.groups, key=lambda x: x.first_occurrence_index)
        group_id = 1
        for group in groups:
            group.id = group_id
            group_id += 1
