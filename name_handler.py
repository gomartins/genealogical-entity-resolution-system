import ast
import re

from person_entities import *
from spacy_utils import SpacyUtils
from utils import Utils

logger = logging.getLogger('logger')
config = ConfigHandler()
utils = SpacyUtils()

GEN_TITLES = ast.literal_eval(config.get('GENERATIONAL_TITLES'))
ROYAL_TITLES = ast.literal_eval(config.get('ROYAL_TITLES'))
ARMY_TITLES = ast.literal_eval(config.get('ARMY_TITLES'))
COURTESY_TITLES = ast.literal_eval(config.get('COURTESY_TITLES'))
OTHER_TITLES = ast.literal_eval(config.get('OTHER_TITLES'))


class FirstNameEntry(object):

    def __init__(self, total_count, overall_frequency, female_count, male_count, female_proportion, male_proportion):
        self.total_count = total_count
        self.overall_frequency = overall_frequency
        self.female_count = female_count
        self.male_count = male_count
        self.female_proportion = female_proportion
        self.male_proportion = male_proportion

    def is_first_name(self):
        return self.overall_frequency > float(config.get('MIN_FIRST_NAME_FREQUENCY_THRESHOLD'))

    def get_overall_frequency(self):
        return self.overall_frequency

    def get_gender(self):
        if self.is_first_name():
            return GENDER_MALE if self.male_count > self.female_count else GENDER_FEMALE
        return None


class FirstNameDataset(object):

    @staticmethod
    def get_names():
        names = {}
        with open(FIRST_NAMES_DATASET, 'r') as reader:
            next(reader)  # skip header
            for line in reader:
                parts = line.strip().split(",")
                name = parts[0].lower()
                total_count = int(parts[1])
                overall_freq = float(parts[2])
                f_count = int(parts[3])
                m_count = int(parts[4])
                f_proportion = float(parts[5])
                m_proportion = float(parts[6])
                names[name] = FirstNameEntry(total_count, overall_freq, f_count, m_count, f_proportion, m_proportion)
        return names


class PronounHandler(object):

    def get_gender(self, pronoun):
        return PRONOUNS[str(pronoun).lower()]

    def is_pronoun(self, pronoun):
        return True if pronoun.lower() in PRONOUNS else False


class NameHandler(object):

    def __init__(self):
        self.names = FirstNameDataset.get_names()
        self.non_existing_name = FirstNameEntry(0, 0, 0, 0, 0, 0)

    def get(self, name):
        if name and name.lower().strip() in self.names:
            return self.names[name.lower()]
        return self.non_existing_name

    def get_gender(self, name):
        return self.get(name).get_gender()

    def look_for_generational_title(self, parts):
        return self.__default_token_search(GEN_TITLES, parts, None, regex="[.,]")

    def look_for_courtesy_title(self, parts, span):
        return self.__default_token_search(COURTESY_TITLES, parts, span, regex="[.]", part_idx=0)

    def look_for_royal_title(self, parts, span):
        return self.__default_token_search(ROYAL_TITLES, parts, span, part_idx=0)

    def look_for_army_title(self, parts, span):
        return self.__default_token_search(ARMY_TITLES, parts, span, part_idx=0)

    def look_for_other_title(self, parts, span):
        return self.__default_token_search(OTHER_TITLES, parts, span)

    def look_for_last_name_prior_wedding(self, parts):
        found = [value for value in parts if value[0] == '(' or value[0] == "["]
        if found:
            return found[0]
        if len(parts) == 2 and parts[0] == TOKEN_NEE:
            return parts[1]

    def look_for_nickname(self, parts):
        start_token = [value for value in parts if value[0] == '"']
        end_token = [value for value in parts if value[-1] == '"']
        if start_token and end_token:
            return parts[parts.index(start_token[0]):parts.index(end_token[0]) + 1]
        if start_token and not end_token:
            return start_token


    def get_courtesy_gender(self, title):
        text = self.__strip_text(str(title), clear_char=".")
        female_titles = ['mrs', 'ms', 'miss']
        return GENDER_FEMALE if text in female_titles else GENDER_MALE

    def exclude_unwanted_words(self, parts):
        return [entry for entry in parts if entry.lower() not in [TOKEN_NEE]]

    def process_parts(self, data, parts, span):
        title = self.look_for_generational_title(parts)
        if title:
            data[PERSON_GEN_TITLE] = title.replace(".", "").replace(",", "").strip()
            parts.remove(title)
            if parts:
                parts[-1] = parts[-1].replace(",", "")  # Remove comma from names such as Alpheus Spring Packard, Sr

        courtesy = self.look_for_courtesy_title(parts, span)
        if courtesy:
            data[PERSON_COURTESY_TITLE] = courtesy.replace(".", "").strip()
            self.__clear_parts(courtesy, parts)

        last_name_prior_wedding = self.look_for_last_name_prior_wedding(parts)
        if last_name_prior_wedding:
            data[PERSON_LAST_NAME_PRIOR_WEDDING] = Utils.replace_str(last_name_prior_wedding, "[][)(]", "")
            self.__clear_parts(last_name_prior_wedding, parts)

        nickname = self.look_for_nickname(parts)
        if nickname:
            data[PERSON_NICKNAME] = " ".join(nickname).replace('"', "").replace("'", "").strip()
            self.__clear_parts(nickname, parts)

        royal_title = self.look_for_royal_title(parts, span)
        if royal_title:
            data[PERSON_ROYAL_TITLE] = royal_title
            self.__clear_parts(royal_title, parts)

        army_title = self.look_for_army_title(parts, span)
        if army_title:
            data[PERSON_ARMY_TITLE] = army_title
            data[PERSON_ARMY_RELATED] = True
            self.__clear_parts(army_title, parts)

        other_title = self.look_for_other_title(parts, span)
        if other_title:
            data[PERSON_OTHER_TITLE] = other_title
            self.__clear_parts(other_title, parts)

        parts = self.exclude_unwanted_words(parts)
        return parts

    def to_person(self, attrs, known_names_map=None):

        span = list(attrs.keys())[0]
        full_entry = str(span)

        data = attrs[span]
        data['span'] = span
        text = span.text.lower()
        if len(span) == 1 and text in PRONOUNS:
            data['pronoun'] = full_entry
            data[PERSON_GENDER] = PRONOUNS[text] if text in PRONOUNS else None
            return data

        data[PERSON_FULL_NAME] = full_entry
        clear_full_entry = Utils.replace_str(full_entry, '[([](n[eé]+|or) ', "(").strip()
        parts = clear_full_entry.split()
        parts = self.process_parts(data, parts, span)

        if len(parts) == 0:
            return data

        first_part = parts[0]
        name_dictionary = self.get(Utils.remove_accents(first_part))

        if len(parts) == 1:
            self.process_single_name_person(data, first_part, known_names_map, name_dictionary)
        elif len(parts) == 2:
            self.process_two_name_person(data, first_part, parts)
        else:
            self.process_multiple_name_person(data, first_part, parts)

        data[PERSON_GENDER] = name_dictionary.get_gender()
        self.review_gender(data)
        self.__normalize_data(data)

        for prop in [PERSON_FIRST_NAME, PERSON_LAST_NAME, PERSON_NICKNAME, PERSON_LAST_NAME_PRIOR_WEDDING]:
            if data.get(prop):
                data[prop] = data[prop].replace(",", "")

        return data

    @staticmethod
    def process_multiple_name_person(data, first_part, parts):
        data[PERSON_FIRST_NAME] = first_part
        data[PERSON_LAST_NAME] = parts[-1]
        data[PERSON_MIDDLE_NAMES] = parts[1:-1]

    @staticmethod
    def process_two_name_person(data, first_part, parts):
        data[PERSON_FIRST_NAME] = first_part
        data[PERSON_LAST_NAME] = parts[1]

    @staticmethod
    def process_single_name_person(data, first_part, known_names_map, name_dictionary):
        if first_part.lower() in known_names_map['last_names']:
            data[PERSON_LAST_NAME] = first_part
        elif first_part.lower() in known_names_map['nicknames']:
            data[PERSON_NICKNAME] = first_part
        elif first_part.lower() in known_names_map['first_names'] or name_dictionary.is_first_name():
            data[PERSON_FIRST_NAME] = first_part
        else:
            data[PERSON_LAST_NAME] = first_part

    def review_gender(self, data):
        if not data.get(PERSON_GENDER) and data.get(PERSON_LAST_NAME_PRIOR_WEDDING):
            data[PERSON_GENDER] = GENDER_FEMALE

        if data.get(PERSON_COURTESY_TITLE):
            title_gender = self.get_courtesy_gender(data.get(PERSON_COURTESY_TITLE))
            if data.get(PERSON_GENDER):
                logger.debug("Overriding person gender %s, %s", data, title_gender)
            data[PERSON_GENDER] = title_gender

        if not data.get(PERSON_GENDER) and (data.get(PERSON_ARMY_TITLE) or data.get(PERSON_GEN_TITLE)):
            data[PERSON_GENDER] = GENDER_MALE

        if not data.get(PERSON_GENDER):
            logger.debug("Person entry has no gender (this is expected for last names and others): %s", data)

    @staticmethod
    def __clear_parts(token, parts):
        if isinstance(token, list):
            for tk in token:
                if tk in parts:
                    parts.remove(tk)
        elif token in parts:
            parts.remove(token)

    @staticmethod
    def __strip_text(text, clear_char=None):
        text = text.lower()
        if clear_char:
            text = text.replace(clear_char, "")
        return text.strip()

    @staticmethod
    def __strip_text_regex(text, regex=None):
        text = text.lower()
        if regex:
            text = re.sub(regex, "", text)
        return text.strip()

    @staticmethod
    def __normalize_data(data):
        attrs_to_normalize = [PERSON_LAST_NAME_PRIOR_WEDDING, PERSON_NICKNAME]
        for attr in attrs_to_normalize:
            entry = data.get(attr)
            if entry and isinstance(entry, list):
                if len(entry) == 1:
                    data[attr] = entry[0]
                else:
                    logger.warning("Multiple values for property %s: %s", attr, entry)

    def __default_token_search(self, def_list, parts, span, regex=None, part_idx=None):
        if parts and part_idx is not None:
            parts = [parts[part_idx]]

        titles_found = [value for value in parts if self.__strip_text_regex(value, regex=regex) in def_list]
        if titles_found:
            if str(titles_found[0]).lower() in ['junior', 'senior']:
                print("Should normalize this title to Jr or Sr.!", span, titles_found)
            return titles_found[0]
        if span:
            prev_token = utils.get_prev_token(span)
            if self.__strip_text_regex(str(prev_token), regex=regex) in def_list:
                return str(prev_token)



