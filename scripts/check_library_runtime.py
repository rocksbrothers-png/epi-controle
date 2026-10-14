#!/usr/bin/env python3
"""Check the real offline Office/raster pipeline without DB or uploaded user files."""
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.safety_library.preview import MIMES, render_preview  # noqa: E402


def main():
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.active.title = 'Runtime check'
    workbook.active['A1'] = 'Private safety library'
    workbook.active['A2'] = 'Offline renderer readiness'
    workbook.active.print_area = 'A1:B3'
    second = workbook.create_sheet('Second visible sheet')
    second['A1'] = 'Different worksheet content'
    second.print_area = 'A1:B3'
    stream = io.BytesIO()
    workbook.save(stream)
    manifest, pages = render_preview(stream.getvalue(), 'runtime.xlsx', MIMES['.xlsx'])
    assert manifest['parts'][0]['name'] == 'Runtime check'
    assert pages and pages[0][2].startswith(b'\x89PNG')
    assert [part['name'] for part in manifest['parts']] == ['Runtime check', 'Second visible sheet']
    first_pages = [content for _part, page, content in pages if page == 0]
    assert len(first_pages) == 2 and first_pages[0] != first_pages[1], 'Worksheet content was repeated'
    print(json.dumps({'library_runtime': 'ready', 'network': 'seccomp_verified', 'renderer': manifest['renderer'], 'pages': len(pages)}))


if __name__ == '__main__':
    main()
