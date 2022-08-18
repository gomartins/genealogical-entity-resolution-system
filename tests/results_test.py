import unittest
import spacy
from constants import *
from named_entity_recognition import PersonRecognition
from scrapper import Scrapper
from spacy_helper import CrossDocumentResolution
from validation import ValidationHelper
import itertools as it
from tests.test_constants import TEST_SET


config = ConfigHandler()


class ResultsTest(unittest.TestCase):

    def setUp(self):
        self.nlp = spacy.load("en_core_web_trf", disable=["lemmatizer", "textcat"])
        self.dataset = TEST_SET

    def test_entity_resolution_and_relationship_extraction_score(self):
        param_grid = {
            'MIN_FIRST_NAME_FREQUENCY_THRESHOLD': ['0.00001'],
            'GROUP_SIMILARITY_THRESHOLD': ['0.55'],
            'NAME_COMPARISON_THRESHOLD_OVERALL': ['0.90'],
            'NAME_COMPARISON_THRESHOLD_CORE': ['0.95'],
        }

        parameter_list = self.__get_grid_product(param_grid)
        best_avg_params = {}
        best_recall_params = {}
        best_precision_params = {}
        best_avg = 0
        best_recall = 0
        best_precision = 0

        for parameters in parameter_list:
            config.set_values(parameters)

            validation = ValidationHelper(self.dataset)
            exclusion_map = validation.get_exclusion_map()

            cdr = CrossDocumentResolution(self.nlp, exclusion_map=exclusion_map)
            groups = cdr.resolve(self.dataset)

            validation.get_personal_data_score(groups)

            scores = validation.get_scores(groups)['all']
            if scores['avg'] > best_avg:
                best_avg = scores['avg']
                best_avg_params = parameters

            precision_avg = (scores['muc'][0] + scores['b3'][0] + scores['ceaf_e'][0] + scores['ceaf_m'][0]) / 4
            if precision_avg > best_precision:
                best_precision = precision_avg
                best_precision_params = parameters

            recall_avg = (scores['muc'][1] + scores['b3'][1] + scores['ceaf_e'][1] + scores['ceaf_m'][1]) / 4
            if recall_avg > best_recall:
                best_recall = recall_avg
                best_recall_params = parameters

        print("Best Avg. F-score: ", best_avg, best_avg_params)
        print("Best Precision Score: ", best_precision, best_precision_params)
        print("Best Recall Score: ", best_recall, best_recall_params)

    def test_named_entity_recognition_score(self):
        scrapper = Scrapper()
        validation = ValidationHelper(self.dataset)
        validation_map = validation.validation_map
        document_map = {}

        for entity_validation in validation_map:
            for reference in validation_map[entity_validation]:
                span_range = (reference.char_start, reference.char_end)
                doc_id = reference.source_document
                if doc_id in document_map:
                    document_map[doc_id].append(span_range)
                else:
                    document_map[doc_id] = [span_range]

        metrics = {}

        for entry in self.dataset:
            resolution = PersonRecognition()
            total_expected = len(document_map[entry])
            metrics[entry] = {'matches': 0, 'non_matches': 0, 'total_expected': total_expected}
            text = scrapper.get_wiki_text(entry).strip()
            doc = self.__get_doc(text)
            spans = resolution.get_person_spans(doc)
            for span in spans:
                found_span_range = (span.start_char, span.end_char)
                if found_span_range in document_map[entry]:
                    metrics[entry]['matches'] = metrics[entry]['matches'] + 1
                else:
                    metrics[entry]['non_matches'] = metrics[entry]['non_matches'] + 1

        average_fscore = 0
        total_expected_overall = sum([entry['total_expected'] for entry in metrics.values()])
        for doc_id in metrics:
            entry = metrics[doc_id]
            entry['precision'] = entry['matches'] / entry['total_expected']
            entry['recall'] = entry['matches'] / (entry['non_matches'] + entry['total_expected'])
            entry['fscore'] = 2 * ((entry['precision'] * entry['recall']) / (entry['precision'] + entry['recall']))
            # Weighted f-score
            average_fscore += entry['fscore'] * entry['total_expected']
            entry['overall_performance_impact'] = ((1 - (entry['fscore'])) * entry[
                'total_expected']) / total_expected_overall
        average_fscore = average_fscore / total_expected_overall
        print("Average f-score: ", average_fscore)
        print({k: v for k, v in
               sorted(metrics.items(), key=lambda item: item[1]['overall_performance_impact'], reverse=True)})

    # Returns the combination of the parameters provided
    def __get_grid_product(self, param_grid):
        return (dict(zip(param_grid.keys(), values)) for values in it.product(*param_grid.values()))

    def __get_closest_annotated_range(self, doc_ranges, found_range):
        closest_range = None
        closest_range_score = 99999999999999
        for doc_range in doc_ranges:
            score = abs(doc_range[0] - found_range[0]) + abs(doc_range[1] - found_range[1])
            if score < closest_range_score:
                closest_range_score = score
                closest_range = doc_range
        return closest_range

    def __get_doc(self, text):
        return self.nlp(text)
