"""Check export safety and link behavior without network access."""

from html.parser import HTMLParser
import json
import re
import unittest

from build_sportsconnect import SOURCE, export


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SportsConnectExportTests(unittest.TestCase):
    def setUp(self):
        self.source = SOURCE.read_text(encoding='utf-8')

    def configure(self, key, **changes):
        match = re.search(r'const LINKS = (\{.*?\});', self.source, re.S)
        links = json.loads(match.group(1))
        links[key].update(changes)
        return self.source[:match.start(1)] + json.dumps(links) + self.source[match.end(1):]

    def test_fragment_is_self_contained_and_shows_team_status(self):
        fragment, _ = export(self.source)
        self.assertIn('id="pso-team-status"', fragment)
        ids = {attrs['id'] for _, attrs in Tags(fragment).tags if 'id' in attrs}
        self.assertIn('href="#pso-shootout-competition"', fragment)
        for tag, attrs in Tags(fragment).tags:
            self.assertNotIn(tag, {'html', 'head', 'body', 'script', 'style', 'iframe', 'noscript'})
            self.assertFalse(any(name.startswith(('on', 'data-')) for name in attrs))
            self.assertNotIn('class', attrs)
            for attribute in ('href', 'src'):
                if attribute in attrs:
                    if attribute == 'href' and attrs[attribute].startswith('#'):
                        self.assertIn(attrs[attribute][1:], ids)
                        self.assertNotIn('target', attrs)
                    else:
                        self.assertTrue(attrs[attribute].startswith(('https://', 'mailto:')))
            if attrs.get('href', '').startswith('https://'):
                self.assertEqual(attrs.get('target'), '_blank')
                self.assertEqual(attrs.get('rel'), 'noopener')

    def test_local_pdfs_wait_for_published_urls(self):
        fragment, pending = export(self.configure('rules', url='docs/rules.pdf', enabled=True, sportsConnectUrl=''))
        self.assertIn('rules', pending)
        self.assertIn('Tournament Rules — coming soon', fragment)
        self.assertNotIn('href="docs/', fragment)

    def test_public_url_updates_every_repeated_link(self):
        fragment, pending = export(self.configure('rules', enabled=True, sportsConnectUrl='https://example.org/rules.pdf?a=1&b=2'))
        self.assertNotIn('rules', pending)
        self.assertEqual(fragment.count('href="https://example.org/rules.pdf?a=1&amp;b=2"'), 5)
        self.assertNotIn('Tournament Rules — coming soon', fragment)

    def test_public_standalone_url_is_used_when_override_is_empty(self):
        fragment, pending = export(self.configure('rules', url='https://example.org/rules.pdf', enabled=True, sportsConnectUrl=''))
        self.assertNotIn('rules', pending)
        self.assertEqual(fragment.count('href="https://example.org/rules.pdf"'), 5)

    def test_local_pdf_without_override_stays_pending(self):
        match = re.search(r'const LINKS = (\{.*?\});', self.source, re.S)
        links = json.loads(match.group(1))
        links['rules'] = {'url': 'docs/rules.pdf', 'enabled': True}
        source = self.source[:match.start(1)] + json.dumps(links) + self.source[match.end(1):]
        fragment, pending = export(source)
        self.assertIn('rules', pending)
        self.assertNotIn('href="docs/', fragment)

    def test_disabled_local_link_does_not_require_public_url(self):
        fragment, pending = export(self.configure('schedule', url='docs/schedule.pdf', enabled=False))
        self.assertNotIn('schedule', pending)
        self.assertIn('Game Schedule</span>', fragment)

    def test_image_uses_public_source_when_override_is_empty(self):
        fragment, _ = export(self.configure('fieldMap', sportsConnectUrl=''))
        images = [attrs for tag, attrs in Tags(fragment).tags if tag == 'img']
        self.assertTrue(any(attrs['src'].endswith('small.jpg') for attrs in images))

    def test_invalid_image_destination_is_rejected(self):
        for value in ('https://', 'mailto:someone@example.org', 'images/map.jpg'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                export(self.configure('fieldMap', sportsConnectUrl=value))

    def test_cached_styles_do_not_share_inline_overrides(self):
        source = self.source.replace('data-link="rules"',
                                     'style="letter-spacing:9px;" data-link="rules"', 1)
        fragment, _ = export(source)
        styled = [attrs for _, attrs in Tags(fragment).tags
                  if 'letter-spacing:9px' in attrs.get('style', '')]
        self.assertEqual(len(styled), 1)

    def test_disabled_link_has_no_clickable_destination(self):
        fragment, _ = export(self.configure('teamRegistration', url='https://example.org/registration', enabled=False))
        self.assertNotIn('href="https://example.org/registration"', fragment)
        self.assertEqual(fragment.count('Team Registration</span>'), 1)
        self.assertEqual(fragment.count('Register Your Team</span>'), 2)

    def test_invalid_published_url_is_rejected(self):
        for value in ('docs/rules.pdf', 'javascript:alert(1)'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                export(self.configure('rules', sportsConnectUrl=value))


if __name__ == '__main__':
    unittest.main()
