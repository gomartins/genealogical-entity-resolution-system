from bs4 import BeautifulSoup

from constants import WIKIPEDIA_DATA_LOCATION


class Anchor(object):

    def __init__(self, element):
        self.text = element.text
        self.href = element['href']
        self.title = element['title'] if 'title' in element else None

    def __repr__(self):
        return "Text: [{0}] Href: [{1}]".format(self.text, self.href)


class Scrapper(object):

    def get_text(self, path, selector, exclude_selectors=None):
        if exclude_selectors is None:
            exclude_selectors = []
        text = ''
        with open(path, 'r', encoding="utf8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            for exclude in exclude_selectors:
                for s in soup.select(exclude):
                    s.extract()
            eles = soup.select(selector)
            for ele in eles:
                text += ele.get_text()
        return text

    def get_anchors(self, path, selector, exclude_selectors=None):
        anchors = []
        if exclude_selectors is None:
            exclude_selectors = []
        with open(path, 'r', encoding="utf8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            for exclude in exclude_selectors:
                for s in soup.select(exclude):
                    s.extract()
        eles = soup.select(selector)
        for ele in eles:
            if 'href' not in ele:
                continue
            if 'index.php' not in ele['href']:
                parent_text = ele.parent.text
                ele_text_idx = parent_text.index(ele.text)
                base_offset = 10
                left_offset = min(ele_text_idx, base_offset)
                right_offset = base_offset if ele_text_idx + len(ele.text) + base_offset <= len(parent_text) else len(parent_text) - (len(ele.text) + ele_text_idx)
                if right_offset < base_offset:
                    print("Right offset is 0!")
                surrounding_text = parent_text[ele_text_idx - left_offset:ele_text_idx + len(ele.text) + right_offset]
                data = {'href': ele['href'], 'parent_text': parent_text, 'surrounding_text': surrounding_text,
                        'left_offset': left_offset, 'right_offset': right_offset, 'text': ele.text}
                anchors.append(data)
        return anchors

    def get_wiki_anchors(self, article_name):
        selector = '#mw-content-text p a'
        exclusion_selectors = ['.reference', '.rt-commentedText', 'a[href*="Pronunciation_respelling_key"]']
        path = '{}/{}.html'.format(WIKIPEDIA_DATA_LOCATION, article_name)
        return self.get_anchors(path, selector, exclude_selectors=exclusion_selectors)

    def get_wiki_text(self, article_name):
        selector = '#mw-content-text p'
        exclusion_selectors = ['.reference', '.rt-commentedText', 'a[href*="Pronunciation_respelling_key"]']
        path = '{}/{}.html'.format(WIKIPEDIA_DATA_LOCATION, article_name)
        # Replace line breaks and non-breaking space by regular spaces
        return self.get_text(path, selector, exclude_selectors=exclusion_selectors)\
            .replace("\n", " ")\
            .replace(u'\xa0', " ").strip()
