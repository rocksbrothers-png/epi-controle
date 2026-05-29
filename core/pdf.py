"""Utilitários de geração de PDF."""
import base64


def pdf_safe_text(value):
    text = str(value or '')
    text = text.encode('cp1252', 'replace').decode('cp1252')
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def extract_jpeg_dimensions(image_bytes):
    if not image_bytes.startswith(b'\xff\xd8'):
        raise ValueError('JPEG inválido.')
    offset = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    standalone_markers = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9}

    while offset < len(image_bytes):
        while offset < len(image_bytes) and image_bytes[offset] != 0xFF:
            offset += 1
        while offset < len(image_bytes) and image_bytes[offset] == 0xFF:
            offset += 1
        if offset >= len(image_bytes):
            break

        marker_byte = image_bytes[offset]
        offset += 1

        if marker_byte in standalone_markers:
            continue
        if offset + 2 > len(image_bytes):
            break

        segment_length = int.from_bytes(image_bytes[offset:offset + 2], 'big')
        if segment_length < 2 or offset + segment_length > len(image_bytes):
            break

        if marker_byte in sof_markers:
            segment_start = offset + 2
            if segment_start + 5 > len(image_bytes):
                break
            height = int.from_bytes(image_bytes[segment_start + 1:segment_start + 3], 'big')
            width = int.from_bytes(image_bytes[segment_start + 3:segment_start + 5], 'big')
            if width > 0 and height > 0:
                return width, height

        offset += segment_length

    return 1, 1


def extract_pdf_logo_image(data_uri):
    value = str(data_uri or '')
    if not value.startswith('data:image/jpeg;base64,') and not value.startswith('data:image/jpg;base64,'):
        return None
    image_bytes = base64.b64decode(value.split(',', 1)[1])
    width, height = extract_jpeg_dimensions(image_bytes)
    return {'bytes': image_bytes, 'width': width, 'height': height}


def build_pdf_document(page_lines, header_image=None):
    objects = []

    def add_object(content):
        objects.append(content)
        return len(objects)

    catalog_id = add_object('')
    pages_id = add_object('')
    font_regular_id = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    font_bold_id = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>')
    image_object_id = None
    if header_image:
        image_stream = header_image['bytes']
        image_object_id = add_object(
            f"<< /Type /XObject /Subtype /Image /Width {header_image['width']} /Height {header_image['height']} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(image_stream)} >>\nstream\n".encode('latin-1')
            + image_stream
            + b"\nendstream"
        )
    page_ids = []
    for lines in page_lines:
        commands = ['q 0.96 0.85 0.78 rg 40 770 515 44 re f Q']
        if image_object_id:
            commands.append('q 72 0 0 36 452 774 cm /Im1 Do Q')
        for line in lines:
            font = '/F2' if line.get('bold') else '/F1'
            size = line.get('size', 12)
            x = line.get('x', 50)
            y = line.get('y', 760)
            commands.append(f"BT {font} {size} Tf 1 0 0 1 {x} {y} Tm ({pdf_safe_text(line.get('text', ''))}) Tj ET")
        content_stream = '\n'.join(commands).encode('cp1252', 'replace')
        content_id = add_object(f"<< /Length {len(content_stream)} >>\nstream\n".encode('latin-1') + content_stream + b"\nendstream")
        image_resource = f" /XObject << /Im1 {image_object_id} 0 R >>" if image_object_id else ''
        page_id = add_object(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >>{image_resource} >> /Contents {content_id} 0 R >>")
        page_ids.append(page_id)
    kids = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>"
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>"

    output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        if isinstance(obj, bytes):
            output.extend(f"{index} 0 obj\n".encode('latin-1'))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        else:
            output.extend(f"{index} 0 obj\n{obj}\nendobj\n".encode('latin-1'))
    xref_pos = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode('latin-1'))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode('latin-1'))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode('latin-1'))
    return bytes(output)
