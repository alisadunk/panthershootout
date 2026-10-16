"""Check native PDF fields, unchanged artwork, and saved values.

These checks require PyMuPDF, as does make_forms_fillable.py.
"""

import unittest

try:
    import fitz
except ImportError:
    fitz = None

if fitz is not None:
    from make_forms_fillable import BUILDERS, ROOT


@unittest.skipIf(fitz is None, 'PyMuPDF is required for PDF checks')
class FillableFormTests(unittest.TestCase):
    def test_deliverables_are_blank_unique_printable_fields(self):
        counts = {'6 Application 2026.pdf': 31, '11 Ref Nomination 2026.pdf': 54,
                  '12 Youth Referee 2026.pdf': 31, '8 Guest Player 2026.pdf': 50}
        for filename, expected in counts.items():
            with self.subTest(filename=filename), fitz.open(ROOT / 'docs' / filename) as doc:
                widgets = [w for page in doc for w in (page.widgets() or [])]
                self.assertEqual(len(widgets), expected)
                self.assertEqual(len({w.field_name for w in widgets}), expected)
                for widget in widgets:
                    self.assertIn(widget.field_value, ('', 'Off'))
                    self.assertTrue(widget.field_label)
                    self.assertTrue(doc.xref_get_key(widget.xref, 'F')[1] == '4')

    def test_builders_preserve_blank_artwork_and_printed_content(self):
        for filename, builder in BUILDERS.items():
            with self.subTest(filename=filename), fitz.open(ROOT / 'docs' / filename) as doc:
                for page in doc:
                    for widget in list(page.widgets() or []):
                        page.delete_widget(widget)
                originals = [(page.get_text(), page.get_pixmap().samples) for page in doc]
                builder(doc)
                self.assertEqual(len(doc), len(originals))
                for index, page in enumerate(doc):
                    self.assertEqual(page.get_text(), originals[index][0])
                    self.assertEqual(page.get_pixmap().samples, originals[index][1])
                    for widget in page.widgets() or []:
                        self.assertTrue(page.rect.contains(widget.rect))

    def test_text_and_checkbox_values_survive_save_and_reopen(self):
        for filename in BUILDERS:
            with self.subTest(filename=filename), fitz.open(ROOT / 'docs' / filename) as doc:
                expected = {}
                for page in doc:
                    for widget in page.widgets() or []:
                        value = (widget.on_state() if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX
                                 else ('Sample\nAddress' if widget.field_flags & fitz.PDF_TX_FIELD_IS_MULTILINE
                                       else 'Test'))
                        widget.field_value = value
                        widget.update()
                        expected[widget.field_name] = value
                with fitz.open(stream=doc.tobytes(), filetype='pdf') as saved:
                    actual = {w.field_name: w.field_value for page in saved for w in (page.widgets() or [])}
                    self.assertEqual(actual, expected)

    def test_required_ink_signature_areas_remain_clear(self):
        signature_areas = {
            '6 Application 2026.pdf': (1, [(108, 590, 396, 608), (416, 693, 576, 710)]),
            '11 Ref Nomination 2026.pdf': (0, [(31, 665, 594, 699)]),
            '12 Youth Referee 2026.pdf': (0, [(31, 681, 593, 701)]),
            '8 Guest Player 2026.pdf': (0, [(301, 514, 523, 528), (301, 655, 523, 670)]),
        }
        for filename, (page_number, rectangles) in signature_areas.items():
            with self.subTest(filename=filename), fitz.open(ROOT / 'docs' / filename) as doc:
                for widget in doc[page_number].widgets() or []:
                    for bounds in rectangles:
                        self.assertFalse(widget.rect.intersects(fitz.Rect(bounds)), widget.field_name)


if __name__ == '__main__':
    unittest.main()
