import logging
import spacy
from spacy.tokens import Token
from constants import ConfigHandler

logger = logging.getLogger('logger')
config = ConfigHandler()
NAMED_SPAN_PERSON = config.get('SPACY_NAMED_SPAN_PERSON')


class SpacyUtils(object):

    def get_next_token(self, entry):
        if isinstance(entry, spacy.tokens.Span):
            if len(entry.doc) - 1 >= entry.end:
                return entry.doc[entry.end]

        if isinstance(entry, spacy.tokens.Token):
            if len(entry.doc) >= entry.i:
                return entry.doc[entry.i + 1]

    def get_prev_token(self, entry):
        if isinstance(entry, spacy.tokens.Span):
            if entry.start > 0:
                return entry.doc[entry.start - 1]

        if isinstance(entry, spacy.tokens.Token):
            if entry.i > 0:
                return entry.doc[entry.i - 1]

    def is_person_token(self, token):
        return token._.is_person_part

    def find_elements_sequence(self, span, start_at, direction, attr_type, value, max_tokens=5, exclude_ent_types=[]):
        found = self.find_elements(span=span, start_at=start_at, mode=direction, attr_key=attr_type, attr_val=value, max_tokens=max_tokens, exclude_ent_types=exclude_ent_types)
        found.sort(key=lambda x: x.i)
        if found:
            if abs(found[0].i - start_at) != 0:
                return None
        else:
            return None

        last_idx = 0
        filtered = []
        for item in found:
            if last_idx == 0:
                last_idx = item.i
                filtered.append(item)
            elif last_idx + 1 == item.i:
                last_idx = item.i
                filtered.append(item)
        return filtered

    def find_element(self, span=None, start_at=None, mode=None, attr_key=None, attr_val=None, max_tokens=5, ext=False):
        found = self.find_elements(span=span, start_at=start_at, mode=mode, attr_key=attr_key, attr_val=attr_val, max_tokens=max_tokens, ext=ext)
        if found:
            return found[0]

    def find_elements(self, span=None, start_at=None, mode=None, attr_key=None, attr_val=None, max_tokens=5, ext=False, exclude_ent_types=[]):
        found = []
        if mode == "forward" or mode == "both":
            span_after = span.doc[start_at:span.end]
            for token in span_after:
                if token.i > (max_tokens + start_at):
                    break
                attr = self.get_attr(token=token, attr_name=attr_key, ext=ext)
                if attr == attr_val and token.ent_type_ not in exclude_ent_types:
                    found.append(token)

        if mode == "backward" or mode == "both":
            span_before = span.doc[span.start:start_at]
            for token in span_before:
                if token.i < (start_at - max_tokens):
                    continue  # cannot break
                attr = self.get_attr(token=token, attr_name=attr_key, ext=ext)
                if attr == attr_val and token.ent_type_ not in exclude_ent_types:
                    found.append(token)
        return found

    def get_attr(self, token=None, attr_name=None, ext=False):
        if ext:
            return getattr(getattr(token, '_'), attr_name)
        return getattr(token, attr_name)

    def get_span_range(self, span):
        return "{0}:{1}".format(span.start_char, span.end_char)

    def initialize_person_entities(self, document, person_name_spans):
        names_token_index = {}
        for span in person_name_spans:
            for token in span:
                names_token_index[token.i] = span
        Token.set_extension("get_person", getter=lambda token: names_token_index[token.i] if token.i in names_token_index else None, force=True)
        Token.set_extension("is_person_part", getter=lambda token: token.i in names_token_index, force=True)
        document.spans[NAMED_SPAN_PERSON] = person_name_spans
