import logging
import unicodedata
import unidecode
import re

logger = logging.getLogger('logger')


class Utils(object):

    @staticmethod
    def is_str_equals_ignore_case(str1, str2):
        if not str1 or not str2:
            return False
        return str1.lower().strip() == str2.lower().strip()

    @staticmethod
    def is_str_empty_or_equals_ignore_case(str1, str2):
        if str1 and str2:
            return str1.lower() == str2.lower()
        if not str1 and not str2:
            return True
        return False

    @staticmethod
    def jaccard_similarity(list1, list2):
        intersection = len(list(set(list1).intersection(list2)))
        union = (len(list1) + len(list2)) - intersection
        if union == 0:
            return 0
        result = float(intersection) / union
        logger.debug("Jaccard for %s and %s: %s", list1, list2, result)
        return result

    @staticmethod
    def merge_dictionaries(list_of_dicts):
        return dict(pair for d in list_of_dicts for pair in d.items())

    @staticmethod
    def most_frequent(items, case_sensitive=True):
        if items:
            items = Utils.flatten_list(items)
            if not case_sensitive:
                items = [item.lower() for item in items]

            # For strings, if there is a draw, we prefer the largest entry
            # (eg. ['B', 'Bush'] -> Bush should go first and be selected
            items_sorted = sorted(items, key=lambda k: len(k) if isinstance(k, str) else k, reverse=True)
            return max(items_sorted, key=items_sorted.count)

    @staticmethod
    def flatten_list(items):
        rt = []
        for i in items:
            if isinstance(i, list):
                rt.extend(Utils.flatten_list(i))
            else:
                rt.append(i)
        return rt

    @staticmethod
    def normalize_array_properties(props, references):
        for prop in props:
            for reference in references:
                property_value = reference.get(prop)
                if property_value and isinstance(property_value, list):
                    de_duped = set(property_value)
                    if len(de_duped) == 1:
                        reference[prop] = next(iter(de_duped))
                    else:
                        print("Tried to normalize array property, but it has multiple different values! ", de_duped)

    @staticmethod
    def normalize_text_properties(props, references):
        for prop in props:
            for reference in references:
                property_value = reference.get(prop)
                if property_value:
                    if isinstance(property_value, list):
                        print("Property value is a list!", prop, reference, property_value)
                        continue
                    normalized = unicodedata.normalize('NFKD', property_value).lower().replace(".", " ").strip()
                    # Normalizes the number of whitespaces between words
                    normalized = " ".join(normalized.split())
                    reference[prop] = normalized



    @staticmethod
    def remove_accents(text):
        return unidecode.unidecode(text)

    @staticmethod
    def replace_str(text, regex, replacement):
        return re.sub(regex, replacement, text)
