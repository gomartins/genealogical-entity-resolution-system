import re
import logging
logger = logging.getLogger('logger')


class RegexRule(object):

    def __init__(self, regex, group, normalizer=None, maskerizer=None, desc=None):
        self.regex = regex
        self.group = group
        self.normalizer = normalizer
        self.maskerizer = maskerizer
        self.desc = desc


class RegexHandler(object):

    def __init__(self):
        self.rules = {}

    def get_keys(self):
        return self.rules.keys()

    def add_rule(self, identifier, regex, group, normalizer=None, maskerizer=None, postprocessor=None, desc=None):
        rule = RegexRule(regex, group, normalizer=normalizer, maskerizer=maskerizer, desc=desc)
        if identifier in self.rules:
            self.rules[identifier].append(rule)
        else:
            self.rules[identifier] = [rule]

    def __process_maskerizer(self, rule, span):
        return rule.maskerizer.apply_mask(span) if rule.maskerizer else str(span)

    def __process_normalizer(self, rule, span, result):
        return rule.normalizer.normalize(span=span, result=result) if rule.normalizer else result

    def __aggregate_results(self, key, results):
        if key in results:
            if len(results[key]) == 1:
                results[key] = results[key][0]
            else:
                logger.debug("Regex Handler: multiple results for same key!")

    def execute(self, span):
        results = {}
        for key, rules_group in self.rules.items():
            logger.debug("Executing rule id: [%s]", key)
            for rule in rules_group:
                text = self.__process_maskerizer(rule, span)
                logger.debug("Text after mask: %s", text)
                match = re.search(rule.regex, text, re.IGNORECASE)
                if match:
                    found = match.group(rule.group)
                    logger.info("Pattern matched [%s] - Span: %s", found, span)
                    result = self.__process_normalizer(rule, span, found)
                    if result:
                        if key in results:
                            results[key].append(result)
                        else:
                            results[key] = [result]
        return results


