import logging
import pandas as pd
import recordlinkage
from recordlinkage.base import BaseCompareFeature
from recordlinkage.compare import String
from utils import Utils
from constants import ConfigHandler
from sortedcontainers import SortedSet

NAME_PROPERTIES = ["first_name", "last_name", "nickname", "nee", "generational_title"]
logger = logging.getLogger('logger')

config = ConfigHandler()


class RecordLinkage(object):
    """
    Generic Record Linkage class
    """

    def __init__(self, references, index_property):
        # See the following for more details:
        # https://recordlinkage.readthedocs.io/en/latest/notebooks/link_two_dataframes.html
        self.references = references
        self.dataframe = pd.DataFrame.from_records(references, index=index_property)
        indexer = recordlinkage.Index()
        indexer.block(left_on='last_name', right_on='last_name')
        self.candidate_links = indexer.index(self.dataframe)
        self.comparator = recordlinkage.Compare()

    def add_comparator(self, comparator):
        self.comparator.add(comparator)

    def link_records(self, minimum_score):
        features = self.comparator.compute(self.candidate_links, self.dataframe)
        matches = features[features.sum(axis=1) >= minimum_score]
        return self.__get_groups(matches)

    def __get_groups(self, matches_dataframe):
        groups = []
        for first_level in matches_dataframe.index.get_level_values(0):
            temp = SortedSet()  # Make sure this is sorted to guarantee execution consistency
            temp.add(first_level)
            for second_level in matches_dataframe.loc[[first_level]].index.get_level_values(1):
                temp.add(str(second_level))
            group = next((entry for entry in groups if (any(item in entry for item in temp))), None)
            group.update(temp) if group else groups.append(temp)
        logger.debug("Pairs resolved: %s", groups)
        return groups


class CoreRecordLinkage(object):
    """
    This class is responsible for identifying core persons within the same document.
    Core group persons are used as the initial basis for further grouping.
    We should have high confidence they are the same entity.
    """
    def resolve(self, references):
        Utils.normalize_array_properties(['yob', 'yod'], references)

        normalize_names = config.get('RECORD_LINKAGE_NORMALIZE_NAMES')
        if normalize_names and normalize_names.lower() == 'true':
            Utils.normalize_text_properties(NAME_PROPERTIES, references)

        logger.debug("Looking for pairs for core resolution: %s", references)

        comp_algorithm = config.get('NAME_COMPARISON_ALGORITHM')
        comp_threshold = float(config.get('NAME_COMPARISON_THRESHOLD_CORE'))

        link = RecordLinkage(references, "id")
        link.add_comparator(String('first_name', 'first_name', method=comp_algorithm, threshold=comp_threshold, label='first_name'))
        link.add_comparator(String('last_name', 'last_name', method=comp_algorithm, threshold=comp_threshold, label='last_name'))
        link.add_comparator(CompareSoftExact('generational_title', 'generational_title', label='generational_title'))
        min_score = 3
        return link.link_records(min_score)


class CrossDocumentLinkage(object):
    """
    This class is responsible for identifying consolidated persons across different documents.
    Consolidated means a merged object based on multiple references of the same person entity within a document.
    Eg.: Doc1 -> [Michelle Obama, Michelle, She, Her, etc, Born on XYZ] -> Consolidated: Michelle Obama (Born on XYZ)
    """

    def __get_attribute_count(self, reference):
        count = 0
        skip_attrs = ['group_id', 'merged_name']
        for attr in reference:
            found = list(filter(lambda x: x in attr, skip_attrs))
            if found:
                continue
            value = reference[attr]
            if isinstance(value, list):
                count += len([entry for entry in value if entry])
            elif value:
                count += 1
        return count

    def resolve(self, references):
        normalize_names = config.get('RECORD_LINKAGE_NORMALIZE_NAMES')

        if normalize_names and normalize_names.lower() == 'true':
            Utils.normalize_text_properties(NAME_PROPERTIES, references)

        comp_algorithm = config.get('NAME_COMPARISON_ALGORITHM')
        comp_threshold = float(config.get('NAME_COMPARISON_THRESHOLD_OVERALL'))
        link = RecordLinkage(references, "res_and_group_id")

        link.add_comparator(String('first_name', 'first_name', method=comp_algorithm, threshold=comp_threshold, label='first_name'))
        link.add_comparator(String('last_name', 'last_name', method=comp_algorithm, threshold=comp_threshold, label='last_name'))
        link.add_comparator(String('nickname', 'nickname', method=comp_algorithm, threshold=comp_threshold, label='nickname'))
        link.add_comparator(CompareSoftExact('generational_title', 'generational_title', label='generational_title'))
        link.add_comparator(CompareSoftExact('royal_title', 'royal_title', label='royal_title'))
        link.add_comparator(CompareArrayString('middle_names', 'middle_names', label='middle_names', empty_matches=True))
        link.add_comparator(CompareSoftExact('nee', 'nee', label='nee'))
        link.add_comparator(CompareSoftExact('yob', 'yob', label='yob'))
        link.add_comparator(CompareSoftExact('yod', 'yod', label='yod'))

        min_score = 8
        return link.link_records(min_score)  # This returns only the pairs found in the link


class CompareArrayString(BaseCompareFeature):

    def __init__(self, labels_left, labels_right, args=(), kwargs={}, label=None, empty_matches=False):
        super().__init__(labels_left, labels_right, args, kwargs, label=label)
        self.empty_matches = empty_matches

    def _compute_vectorized(self, s1, s2):
        results = []
        for d1, d2 in zip(s1.fillna(""), s2.fillna("")):
            if not d1 or not d2:
                if self.empty_matches and not d1 and not d2:
                    # We consider the same if they are both empty
                    results.append(1)
                else:
                    results.append(0)
            elif isinstance(d1, list) and isinstance(d2, list):
                results.append(Utils.jaccard_similarity(d1, d2))
            elif isinstance(d1, list) and isinstance(d2, str):
                if d2.lower() in (entry.lower() for entry in d1):
                    results.append(1)
                else:
                    results.append(0)
            elif isinstance(d1, str) and isinstance(d2, list):
                if d1.lower() in (entry.lower() for entry in d2):
                    results.append(1)
                else:
                    results.append(0)
            elif isinstance(d1, str) and isinstance(d2, str):
                if d1.lower() == d2.lower():
                    results.append(1)
                else:
                    results.append(0)
            else:
                logger.error("Unexpected scenario! %s %s", d1, d2)

        return pd.Series(results)


class CompareSoftExact(BaseCompareFeature):

    def _compute_vectorized(self, s1, s2):
        if len([e for e in s1 if isinstance(e, list)]) > 0 or len([e for e in s2 if isinstance(e, list)]) > 0:
            print("Found list in string comparator!")
        # returns true if both are empty or equals, or false if they are different
        return (s1.fillna("") == s2.fillna("")).astype(float)
