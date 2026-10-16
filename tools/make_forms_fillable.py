"""Add native PDF fields to the four registration forms without changing artwork.

Requires PyMuPDF. Run from any directory with --output-dir pointing to a review
directory. Source PDFs are never overwritten by this script. Existing signature
lines remain for the ink signatures required by the printed instructions.
"""

import argparse
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]


class Form:
    def __init__(self, document, page_number=0):
        self.document = document
        self.page = document[page_number]
        self.names = set()

    def field(self, name, label, bounds, *, checkbox=False, multiline=False,
              size=9, maxlen=120):
        if name in self.names:
            raise ValueError(f'Duplicate field: {name}')
        self.names.add(name)
        widget = fitz.Widget()
        widget.field_name = name
        widget.field_label = label
        widget.field_type = (fitz.PDF_WIDGET_TYPE_CHECKBOX if checkbox
                             else fitz.PDF_WIDGET_TYPE_TEXT)
        widget.rect = fitz.Rect(bounds)
        if not self.page.rect.contains(widget.rect):
            raise ValueError(f'Field outside page: {name}')
        widget.field_value = 'Off' if checkbox else ''
        widget.text_font = 'ZaDb' if checkbox else 'Helv'
        widget.text_fontsize = size
        widget.text_color = (0, 0, 0)
        widget.text_maxlen = maxlen
        widget.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE if multiline else 0
        widget.border_width = 0
        widget.border_color = None
        widget.fill_color = None
        annotation = self.page.add_widget(widget)
        self.document.xref_set_key(annotation.xref, 'F', '4')  # Print entered values.

    def check(self, name, label, bounds):
        self.field(name, label, bounds, checkbox=True, size=0)


def application(document):
    form = Form(document, 1)
    for name, label, bounds in (
        ('application_date', 'Application date', (159, 157, 580, 174)),
        ('section', 'AYSO section', (84, 180, 154, 203)),
        ('area', 'AYSO area', (200, 180, 251, 203)),
        ('region', 'Region number and name', (366, 180, 580, 203)),
        ('team_name', 'Team name', (159, 210, 580, 227)),
    ):
        form.field(name, label, bounds)
    for age, x in ((10, 111.2), (12, 162.9), (14, 213.2)):
        form.check(f'division_{age}u', f'Age division {age}U', (x, 237.4, x+10.1, 247.5))
    for gender, x in (('boys', 347.4), ('girls', 416.4)):
        form.check(f'gender_{gender}', gender.title(), (x, 237.4, x+10.1, 247.5))
    rows = (
        ('name', 'Name', 293, 310, False),
        ('email', 'Email', 315, 331, False),
        ('address', 'Mailing address', 336, 384, True),
        ('phone', 'Cell phone', 389, 406, False),
        ('emergency_contact', 'Emergency contact name and phone', 411, 438, True),
        ('ayso_id', 'AYSO ID', 443, 459, False),
        ('certification', 'Certification level', 464, 481, False),
        ('safe_haven_date', 'Safe Haven date', 486, 502, False),
    )
    for role, left, right in (('coach', 143, 304), ('assistant_coach', 413, 574)):
        for name, label, top, bottom, multiline in rows:
            form.field(f'{role}_{name}', f'{role.replace("_", " ").title()}: {label}',
                       (left, top, right, bottom), multiline=multiline)
    for name, label, bounds in (
        ('refund_address', 'Region address for referee deposit refund', (207, 512, 574, 526)),
        ('guest_player_count', 'Number of guest players approved by RC', (166, 676, 190, 688)),
        ('rc_name', 'Regional Commissioner printed name', (84, 694, 250, 708)),
        ('rc_email', 'Regional Commissioner email', (66, 715, 250, 729)),
        ('rc_phone', 'Regional Commissioner phone', (321, 715, 574, 729)),
    ):
        form.field(name, label, bounds)


def referee_nomination(document):
    form = Form(document)
    for name, label, bounds in (
        ('form_date', 'Referee information form date', (498, 129, 586, 147)),
        ('region', 'Region', (90, 152, 159, 171)),
        ('team_name', 'Team name', (243, 152, 586, 171)),
        ('coach_name', 'Coach name', (106, 180, 293, 195)),
        ('contact_name', 'Referee team contact name', (102, 266, 304, 284)),
        ('contact_email', 'Referee team contact email', (399, 266, 579, 284)),
        ('contact_day_phone', 'Referee team contact day phone', (102, 289, 304, 306)),
        ('contact_evening_phone', 'Referee team contact evening phone', (399, 289, 579, 306)),
    ):
        form.field(name, label, bounds)
    for age, x in ((10, 120), (12, 179), (14, 238)):
        form.check(f'division_{age}u', f'Age division {age}U', (x, 217.4, x+10.1, 227.5))
    columns = (
        ('name', 'Name', 46, 180, 9),
        ('badge', 'Badge level (R, I, A, N)', 185, 217, 9),
        ('certification_date', 'Certification date', 222, 264, 7),
        ('center_boys', 'Highest boys division as center referee', 269, 297, 8),
        ('center_girls', 'Highest girls division as center referee', 302, 328, 8),
        ('assistant_boys', 'Highest boys division as assistant referee', 333, 361, 8),
        ('assistant_girls', 'Highest girls division as assistant referee', 366, 394, 8),
        ('player_on_team', 'Child playing on this team (Y/N)', 399, 440, 9),
    )
    for row in range(4):
        top = 417 + row*30
        for name, label, left, right, size in columns:
            form.field(f'referee_{row+1}_{name}', f'Referee {row+1}: {label}',
                       (left, top, right, top+25), size=size)
        form.field(f'referee_{row+1}_phone', f'Referee {row+1}: Home phone',
                   (445, top, 592, top+10), size=8)
        form.field(f'referee_{row+1}_email', f'Referee {row+1}: Email',
                   (445, top+15, 592, top+25), size=8)
    for name, label, left, right in (
        ('rra_name', 'Regional Referee Administrator name', 33, 211),
        ('rra_phone', 'Regional Referee Administrator phone', 245, 367),
        ('rra_email', 'Regional Referee Administrator email', 387, 592),
    ):
        form.field(name, label, (left, 548, right, 575))


def youth_referee(document):
    form = Form(document)
    for name, label, bounds in (
        ('youth_name', 'Youth referee name', (213, 132, 587, 147)),
        ('age', 'Current age', (213, 155, 336, 169)),
        ('date_of_birth', 'Date of birth', (451, 155, 587, 169)),
        ('badge', 'AYSO badge level', (213, 178, 336, 192)),
        ('certification_date', 'Certification date', (451, 178, 587, 192)),
        ('representing_team', 'Representing tournament team', (213, 200, 587, 214)),
        ('region', 'Region', (89, 245, 158, 259)),
        ('team_name', 'Team name', (241, 245, 587, 259)),
        ('coach_name', 'Coach name', (137, 268, 587, 282)),
        ('rra_name', 'Regional Referee Administrator name', (33, 485, 232, 499)),
        ('rra_phone', 'Regional Referee Administrator phone', (249, 485, 372, 499)),
        ('rra_email', 'Regional Referee Administrator email', (390, 485, 592, 499)),
    ):
        form.field(name, label, bounds)
    for age, x in ((10, 120), (12, 179), (14, 238)):
        form.check(f'division_{age}u', f'Team age division {age}U', (x, 301, x+9, 310))
    edges = [297.5, 332.5, 367.5, 402.5, 438.5, 473.5, 508.5, 543.5, 579.5]
    divisions = ('10ug', '10ub', '12ug', '12ub', '14ug', '14ub', '16ug', '16ub')
    for role, top in (('center', 620), ('assistant', 633)):
        for index, division in enumerate(divisions):
            x = (edges[index] + edges[index+1])/2 - 4.5
            form.check(f'{role}_{division}', f'Qualified as {role} referee for {division.upper()}',
                       (x, top, x+9, top+9))


def guest_player(document):
    form = Form(document)
    for name, label, left, right in (
        ('team_name', 'Team name', 39, 225),
        ('area', 'Area', 230, 288),
        ('region', 'Region number', 293, 355),
        ('region_name', 'Region name', 360, 563),
    ):
        form.field(name, label, (left, 224, right, 236))
    for name, label, x in (
        ('division_10u', 'Age division 10U', 280),
        ('division_12u', 'Age division 12U', 340),
        ('division_14u', 'Age division 14U', 406),
        ('gender_boys', 'Boys', 470),
        ('gender_girls', 'Girls', 528),
    ):
        form.check(name, label, (x-4.5, 270, x+4.5, 279))
    form.field('coach_name_address', 'Head coach name and mailing address',
               (129, 318, 262, 371), multiline=True)
    for name, label, left, right in (
        ('coach_home_phone', 'Head coach home phone', 267, 355),
        ('coach_cell_phone', 'Head coach cell phone', 360, 439),
        ('coach_email', 'Head coach email', 444, 562),
    ):
        form.field(name, label, (left, 318, right, 371), size=8, multiline=True)
    edges = [37.5, 69.5, 159.5, 209.5, 370.5, 407.5, 479.5, 573.5]
    columns = ('jersey_number', 'ayso_id', 'home_region', 'name', 'age', 'date_of_birth', 'phone')
    rows = [(421.5, 441.5), (441.5, 461.5), (461.5, 484.5)]
    for row, (top, bottom) in enumerate(rows, 1):
        for index, name in enumerate(columns):
            form.field(f'player_{row}_{name}', f'Guest player {row}: {name.replace("_", " ")}',
                       (edges[index]+2, top+2, edges[index+1]-2, bottom-2), size=8)
    for role, shift in (('team_rc', 0), ('home_rc', 141.2)):
        for name, label, bounds in (
            ('name', 'Printed name', (70, 514, 256, 527)),
            ('address', 'Address', (91, 546, 297, 559)),
            ('city', 'City', (328, 546, 475, 559)),
            ('zip', 'ZIP code', (503, 546, 550, 559)),
            ('phone_area_code', 'Phone area code', (89, 569, 119, 582)),
            ('phone_number', 'Phone number without area code', (123, 569, 204, 582)),
            ('email', 'Email', (244, 569, 377, 582)),
            ('date_signed', 'Date signed', (439, 569, 551, 582)),
        ):
            left, top, right, bottom = bounds
            form.field(f'{role}_{name}', f'{role.replace("_", " ").title()}: {label}',
                       (left, top+shift, right, bottom+shift), size=8)


BUILDERS = {
    '6 Application 2026.pdf': application,
    '11 Ref Nomination 2026.pdf': referee_nomination,
    '12 Youth Referee 2026.pdf': youth_referee,
    '8 Guest Player 2026.pdf': guest_player,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == (ROOT / 'docs').resolve():
        parser.error('Choose a review directory; do not overwrite source PDFs.')
    output.mkdir(parents=True, exist_ok=True)
    for filename, builder in BUILDERS.items():
        with fitz.open(ROOT / 'docs' / filename) as document:
            # Allow rebuilding from a previously generated fillable copy.
            for page in document:
                for widget in list(page.widgets() or []):
                    page.delete_widget(widget)
            builder(document)
            document.xref_set_key(document.pdf_catalog(), 'AcroForm/NeedAppearances', 'false')
            for page in document:
                document.xref_set_key(page.xref, 'Tabs', '/R')
            document.save(output / filename, garbage=4, deflate=True)
            print(f'{filename}: {sum(len(list(p.widgets() or [])) for p in document)} fields')


if __name__ == '__main__':
    main()
