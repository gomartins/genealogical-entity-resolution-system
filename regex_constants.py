###################
# Building blocks #
###################

# Matches Years from 1000 to 2999
REGEX_YEAR_PATTERN = "(?:[12][0-9]{3})"

# Matches 1-31
REGEX_DAY_PATTERN = "(?:[1-9]|[12]\d|3[01])"

# Matches Jan or January, Feb or February, ..., Dec or December
REGEX_MONTH_TEXT_PATTERN = "(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)|" \
                           "May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|" \
                           "Oct(?:ober)|Nov(?:ember)?|Dec(?:ember)?)"

# Matches (0)1-12
REGEX_MONTH_NUMBER_PATTERN = "(?:0?[1-9]|1[012])"

# Matches REGEX_MONTH_TEXT_PATTERN or REGEX_MONTH_NUMBER_PATTERN
REGEX_MONTHS_PATTERN = f"(?:{REGEX_MONTH_TEXT_PATTERN}|{REGEX_MONTH_NUMBER_PATTERN})"

# Matches born or b.
REGEX_BORN_PATTERN = "(?:born|b\.)"

# Matches (July 20, 1843)
REGEX_FULL_DATE_BLOCK_PATTERN = f"({REGEX_MONTHS_PATTERN})\\s+({REGEX_DAY_PATTERN}),?\\s+({REGEX_YEAR_PATTERN})"

# Matches (25 December 1737)
REGEX_FULL_DATE_BLOCK_DF_PATTERN = f"({REGEX_DAY_PATTERN}),?\\s+({REGEX_MONTHS_PATTERN})\\s+({REGEX_YEAR_PATTERN})"

# Matches (May 1786)
REGEX_MONTH_YEAR_BLOCK_PATTERN = f"({REGEX_MONTHS_PATTERN})\\s+({REGEX_YEAR_PATTERN})"

# Matches ( - ) or ( . ) and etc
REGEX_DATE_SEP = "\\s*.\\s*"

##################
# Final patterns #
##################

# Matches (May 5, 1762 – July 20, 1843)
REGEX_FULL_DOB_DOD_PATTERN = f"{REGEX_FULL_DATE_BLOCK_PATTERN}{REGEX_DATE_SEP}{REGEX_FULL_DATE_BLOCK_PATTERN}"

# Matches (25 December 1737 – 18 April 1785)
REGEX_FULL_DOB_DOD_DF_PATTERN = f"{REGEX_FULL_DATE_BLOCK_DF_PATTERN}{REGEX_DATE_SEP}{REGEX_FULL_DATE_BLOCK_DF_PATTERN}"

# Matches (1942–1995)
REGEX_YOB_YOD_PATTERN = f"({REGEX_YEAR_PATTERN}){REGEX_DATE_SEP}({REGEX_YEAR_PATTERN})"

# Matches (born 1998), (b. July 30, 1937)
REGEX_BORN_YEAR = f".*{REGEX_BORN_PATTERN}[^-]*?({REGEX_YEAR_PATTERN})"

# Matches (born August 4, 1961), (b. July 30, 1937)
REGEX_BORN_MONTH = f".*{REGEX_BORN_PATTERN}[^-]*?({REGEX_MONTH_TEXT_PATTERN})"

# Matches (born August 4, 1961), (b. July 30, 1937)
REGEX_BORN_DAY = f"{REGEX_BORN_PATTERN}[^-]*?{REGEX_MONTH_TEXT_PATTERN}\\s*({REGEX_DAY_PATTERN}),\\s*{REGEX_YEAR_PATTERN}"

# Matches (born in 1928)
REGEX_BORN_IN_YEAR = f"born\\s+(?:in|on?)\\s+({REGEX_YEAR_PATTERN})"

# Matches (died in 1928)
REGEX_DIED_IN_YEAR = f"died\\s+(?:in|on?)\\s+({REGEX_YEAR_PATTERN})"

# Matches (born 1653 - May 25, 1709), (1653 - May 25, 1709)
REGEX_YOB_DOD_PATTERN = f"({REGEX_YEAR_PATTERN}){REGEX_DATE_SEP}{REGEX_FULL_DATE_BLOCK_PATTERN}"

# Matches (May 13, 1744 – May 1786)
REGEX_FULL_DOB_PARTIAL_DOD = f"{REGEX_FULL_DATE_BLOCK_PATTERN}{REGEX_DATE_SEP}{REGEX_MONTH_YEAR_BLOCK_PATTERN}"

# Matches (January 26, 1644-1695)
REGEX_FULL_DOB_YOD = f"{REGEX_FULL_DATE_BLOCK_PATTERN}{REGEX_DATE_SEP}({REGEX_YEAR_PATTERN})"

# Matches (Michelle married Barack), (Michelle Obama married Barack Obama)
REGEX_PERSON_MARRY = "_PERSON_.*?(remarried|married).*?_PERSON_"
REGEX_PERSON_MARRY_ALT = "_PERSON_.*?and.*?_PERSON_.*?(remarried|married)"

REGEX_RELATIVES = "sister|brother|son|grandson|great-grandson|daughter|granddaughter|great-granddaughter" \
                  "|mother|grandmother|great-grandmother|father|grandfather|great-grandfather|husband|wife" \
                  "|uncle|aunt|nephew|niece|cousin|mother-in-law|father-in-law|brother-in-law|sister-in-law"

REGEX_PERSON_RELATIVES = f"_PERSON_.*?({REGEX_RELATIVES}).*?_PERSON_"

REGEX_PERSON_CHILDREN_PAIR = f"_PERSON_.*?(son|daughter).*?_PERSON_.*?and.*?_PERSON_"


# Matches (Jack was born on April 21 , 1962 , in Calumet Park , Illinois , to Mary)
REGEX_PERSON_BORN_TO = "_PERSON_.*?(born).*?to.*?_PERSON_"

# Matches (Jack was born on April 21 , 1962 , in Calumet Park , Illinois , to Mary and John)
REGEX_PERSON_BORN_TO_PAIR = "_PERSON_.*?(born).*?to.*?_PERSON_.*?and.*?_PERSON_"
REGEX_PERSON_PARENTS_PAIR = "_PERSON_.*?(parents).*?were.*?_PERSON_.*?and.*?_PERSON_"
# Person's last name before wedding
# Matches Mary Anne O'Shea (née Gill)
REGEX_NAME_NEE = "n[ée]{2}\\s+([a-zA-Z]+)"

REGEX_ENCLOSED_BY_DB_QUOTES = '\"(.*?)\"'
