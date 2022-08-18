import configparser

BASE_DIRECTORY = "<POINT_THIS_VARIABLE_TO_THE_DATA_DIRECTORY>"

FIRST_NAMES_DATASET = BASE_DIRECTORY + "social_security_dataset_transformed.csv"
PARAMETER_FILE_NAME = BASE_DIRECTORY + "parameters.ini"

WIKIPEDIA_DATA_LOCATION = BASE_DIRECTORY + "wikipedia_articles_html/"

MONTH_MAP = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
GENDER_MALE = 'M'
GENDER_FEMALE = 'F'

PRONOUNS = {'he': GENDER_MALE, 'she': GENDER_FEMALE, 'him': GENDER_MALE, 'her': GENDER_FEMALE, 'hers': GENDER_FEMALE,
            'his': GENDER_MALE, 'himself': GENDER_MALE, 'herself': GENDER_FEMALE}

PERSON_FIRST_NAME = 'first_name'
PERSON_MIDDLE_NAMES = 'middle_names'
PERSON_LAST_NAME = 'last_name'
PERSON_LAST_NAME_PRIOR_WEDDING = 'nee'
PERSON_NICKNAME = 'nickname'
PERSON_FULL_NAME = 'full_name'
PERSON_YOD = 'yod'
PERSON_MOB = 'mob'
PERSON_DOB = 'dob'
PERSON_YOB = 'yob'
PERSON_MOD = 'mod'
PERSON_DOD = 'dod'
PERSON_GENDER = 'gender'
PERSON_ROYAL_TITLE = 'royal_title'
PERSON_ARMY_TITLE = 'army_title'
PERSON_ARMY_RELATED = 'army_related'
PERSON_GEN_TITLE = 'generational_title'
PERSON_COURTESY_TITLE = 'courtesy_title'
PERSON_OTHER_TITLE = 'other_title'


TOKEN_AND = "and"
TOKEN_THE = "the"
TOKEN_COMMA = ","
TOKEN_DOT = "."
TOKEN_DB_QUOTES = '"'
TOKEN_VERSUS = 'v.'
TOKEN_NEE = "née"


class ConfigHandler(object):

    def __init__(self):
        self.__read_config_file()
        self.cache = {}

    def __read_config_file(self):
        self.config_file = PARAMETER_FILE_NAME
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        value = self.config['DEFAULT'][key]
        self.cache[key] = value
        return value

    def set(self, key, value):
        self.__read_config_file()
        self.config['DEFAULT'][key] = value
        self.__save_config()
        self.clear_cache()

    def __save_config(self):
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def set_values(self, values):
        self.__read_config_file()
        for key in values:
            self.config['DEFAULT'][key] = str(values[key])
        self.__save_config()
        self.clear_cache()

    def clear_cache(self):
        self.cache.clear()
