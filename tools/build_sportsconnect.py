"""Export the standalone page as a script-free, inline-styled HTML fragment.

Run from any directory: python tools/build_sportsconnect.py
Uses only the Python standard library. Edit the standalone page, then regenerate.
"""

from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'panther_shootout_main.html'
DESTINATION = ROOT / 'panther_shootout_sportsconnect.html'
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
             'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = Element('document')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise ValueError(f'Unbalanced source HTML near </{tag}>')
        self.stack.pop()

    def handle_data(self, text):
        self.stack[-1].children.append(text)

    def handle_entityref(self, name):
        self.handle_data(f'&{name};')

    def handle_charref(self, name):
        self.handle_data(f'&#{name};')

    def handle_comment(self, text):
        self.handle_data(f'<!--{text}-->')


def declarations(text):
    result = {}
    for declaration in text.split(';'):
        if ':' in declaration:
            key, value = declaration.split(':', 1)
            result[key.strip()] = value.strip()
    return result


def export(source):
    match = re.search(r'// BEGIN LINK CONFIG\s+const LINKS = (\{.*?\});\s+// END LINK CONFIG',
                      source, re.S)
    if not match:
        raise ValueError('Expected the JSON-compatible LINKS object in the standalone page')
    links = json.loads(match.group(1))
    css = re.search(r'<style>(.*?)</style>', source, re.S).group(1)
    # The base layout wraps naturally. Media queries and pseudo-selectors cannot
    # be inlined and are deliberately excluded from the CMS fragment.
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S).split('@media', 1)[0]
    rules = []
    for selectors, block in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        for selector in selectors.split(','):
            selector = selector.strip()
            if re.fullmatch(r'\.?[\w-]+', selector):
                rules.append((10 if selector.startswith('.') else 1,
                              selector, declarations(block)))
    rules.sort(key=lambda rule: rule[0])  # Preserve source order within specificity.
    parser = PageParser()
    parser.feed(source)
    parser.close()
    if len(parser.stack) != 1:
        raise ValueError('Unclosed source HTML elements')
    pending = set()

    def render(node):
        if isinstance(node, str):
            return node
        tag = node.tag
        attrs = node.attrs.copy()
        inline = declarations(attrs.get('style', ''))
        if (tag in {'head', 'script', 'style', 'noscript', 'iframe'}
                or 'hidden' in attrs or inline.get('display') == 'none'):
            return ''
        if tag in {'document', 'html', 'body', 'main'}:
            return ''.join(render(child) for child in node.children)

        classes = attrs.get('class', '').split()
        coming_soon = False
        if 'data-link' in attrs:
            key = attrs['data-link']
            link = links[key]
            destination = link.get('sportsConnectUrl', link['url'])
            if not destination and urlsplit(link['url']).scheme in {'https', 'mailto'}:
                destination = link['url']
            if destination:
                parsed = urlsplit(destination)
                if not ((parsed.scheme == 'https' and parsed.netloc)
                        or (parsed.scheme == 'mailto' and parsed.path)):
                    raise ValueError(f'{key}: Sports Connect requires an absolute HTTPS or mailto URL')
            if link['enabled'] and destination:
                attrs['href'] = destination
                if 'btn-muted' in classes:
                    classes.remove('btn-muted')
                    classes.append('btn-ghost')
                if not destination.startswith('mailto:'):
                    attrs.update(target='_blank', rel='noopener')
            else:
                tag = 'span'
                attrs.update(role='link', **{'aria-disabled': 'true'})
                for name in ('href', 'target', 'rel', 'tabindex'):
                    attrs.pop(name, None)
                coming_soon = link['enabled'] and not destination
                if coming_soon:
                    pending.add(key)
                if 'btn' in classes:
                    classes = [c for c in classes if c not in ('btn-primary', 'btn-ghost', 'btn-muted')]
                    classes.append('btn-muted')
        if 'data-image' in attrs:
            image = links[attrs['data-image']]
            attrs['src'] = image.get('sportsConnectUrl', image['url'])
            if not attrs['src'].startswith('https://'):
                raise ValueError('Fragment images require public HTTPS URLs')

        style = {}
        for _, selector, properties in rules:
            if selector == node.tag or (selector.startswith('.') and selector[1:] in classes):
                style.update(properties)
        style.update(inline)
        if 'section' in classes:
            style.update({'font-family': 'Arial,Helvetica,sans-serif',
                          'color': '#111', 'line-height': '1.5'})
        if 'btn' in classes:
            # Keep the browser's native keyboard focus indicator without a style block.
            style.pop('outline', None)
            style.pop('outline-offset', None)
        attrs = {name: value for name, value in attrs.items()
                 if name != 'class' and not name.startswith(('data-', 'on'))}
        if 'id' in attrs:
            attrs['id'] = 'pso-' + attrs['id']
        if style:
            attrs['style'] = ';'.join(f'{name}:{value}' for name, value in style.items()) + ';'
        if tag == 'section':
            tag = 'div'
        attributes = ''.join(f' {name}="{escape(value, quote=True)}"'
                             for name, value in attrs.items() if value is not None)
        start = f'<{tag}{attributes}>'
        if tag in VOID_TAGS:
            return start
        content = ''.join(render(child) for child in node.children)
        if coming_soon:
            content += ' — coming soon'
        return f'{start}{content}</{tag}>'

    output = render(parser.root).strip()
    output = re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+', '\n\n', output)
    header = '<!-- Sports Connect: paste this entire fragment into the HTML/source editor.\n'
    header += 'Generated from panther_shootout_main.html by tools/build_sportsconnect.py.\n'
    header += 'No document wrapper, scripts, style blocks, or relative file links. -->\n'
    return header + output + '\n', pending


def main():
    output, pending = export(SOURCE.read_text(encoding='utf-8'))
    if '--check' in sys.argv:
        if not DESTINATION.exists() or DESTINATION.read_text(encoding='utf-8') != output:
            raise SystemExit('Sports Connect fragment is out of date; run the exporter.')
        print('Sports Connect fragment matches the standalone source.')
    else:
        DESTINATION.write_text(output, encoding='utf-8')
        print(f'Wrote {DESTINATION.name}')
    if pending:
        print('Coming soon until public file URLs are configured: ' + ', '.join(sorted(pending)))


if __name__ == '__main__':
    main()
