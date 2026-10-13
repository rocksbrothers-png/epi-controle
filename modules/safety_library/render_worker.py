"""Standalone worker; no application imports and no credentials."""
import ctypes
import errno
import io
import json
import os
from pathlib import Path
import re
import resource
import struct
import subprocess
import sys
import zipfile


def offline_sandbox():
    if sys.platform != 'linux':
        raise ValueError('O conversor requer Linux com libseccomp.')
    resource.setrlimit(resource.RLIMIT_CPU, (80, 80))
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (100 * 1024**2, 100 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    class Compare(ctypes.Structure):
        _fields_ = [('arg', ctypes.c_uint), ('op', ctypes.c_uint), ('a', ctypes.c_uint64), ('b', ctypes.c_uint64)]
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Compare)]
    ctx = lib.seccomp_init(0x7fff0000)  # ALLOW; deny Internet, tracing, privileged operations.
    if not ctx:
        raise ValueError('Não foi possível iniciar isolamento do conversor.')
    try:
        deny = 0x50000 | errno.EPERM
        for name in ('socket', 'socketpair'):
            # NE AF_UNIX; local UNO pipe permitted, Internet sockets forbidden.
            cmp = Compare(0, 1, 1, 0)
            if lib.seccomp_rule_add_array(ctx, deny, lib.seccomp_syscall_resolve_name(name.encode()), 1, ctypes.byref(cmp)):
                raise ValueError('Filtro de rede indisponível.')
        for name in ('ptrace', 'process_vm_readv', 'process_vm_writev', 'mount', 'umount2', 'bpf', 'keyctl'):
            call = lib.seccomp_syscall_resolve_name(name.encode())
            if call >= 0 and lib.seccomp_rule_add(ctx, deny, call, 0):
                raise ValueError('Filtro do conversor indisponível.')
        if lib.seccomp_load(ctx):
            raise ValueError('Filtro do conversor não pôde ser aplicado.')
    finally:
        lib.seccomp_release(ctx)
    import socket
    try:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        return
    raise ValueError('Isolamento de rede não confirmado.')


def validate_office(path):
    """Bounded inspection, magic first (real XLS can contain embedded ZIP metadata)."""
    data = path.read_bytes()
    if path.suffix == '.xls':
        if not data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
            raise ValueError('Conteúdo não corresponde a XLS.')
        import olefile
        import xlrd
        with olefile.OleFileIO(io.BytesIO(data)) as ole:
            for parts in ole.listdir():
                name = '/'.join(parts).lower()
                if any(word in name for word in ('vba', 'macros', 'objectpool', 'encryptioninfo', 'encryptedpackage')):
                    raise ValueError('Macros, objetos ativos e arquivos cifrados não são permitidos.')
            stream = ole.openstream('Workbook' if ole.exists('Workbook') else 'Book').read()
        pos = 0
        while pos + 4 <= len(stream):
            record, size = struct.unpack_from('<HH', stream, pos)
            value = stream[pos + 4:pos + 4 + size]
            if record == 0x2f or (record == 0x85 and len(value) > 5 and value[5] in (1, 2)):
                raise ValueError('XLS cifrado ou folha de macro não permitido.')
            if record == 0x1ae:  # external workbook / DDE SUPBOOK
                if len(value) < 4 or value[2:4] not in (b'\x01\x04', b'\x01\x3a'):
                    raise ValueError('Referências externas ativas não são permitidas.')
            pos += 4 + size
        book = xlrd.open_workbook(file_contents=data, on_demand=True)
        if len(book.sheets()) > 30:
            raise ValueError('Planilha excede 30 abas.')
        return []
    if not data.startswith(b'PK\x03\x04'):
        raise ValueError('Conteúdo não corresponde a Office Open XML.')
    from defusedxml import ElementTree
    replacements = {}
    warnings = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 3000 or sum(e.file_size for e in entries) > 100 * 1024**2:
            raise ValueError('Arquivo Office excede os limites de descompactação.')
        names = {e.filename.lower() for e in entries}
        prefix = 'word/' if path.suffix == '.docx' else 'xl/'
        if not any(n.startswith(prefix) for n in names) or '[content_types].xml' not in names:
            raise ValueError('Formato Office incompatível com a extensão.')
        for entry in entries:
            name = entry.filename.lower()
            if entry.flag_bits & 1 or entry.file_size / max(entry.compress_size, 1) > 200:
                raise ValueError('Arquivo cifrado ou excessivamente comprimido.')
            if any(w in name for w in ('vbaproject', 'macrosheet', '/embeddings/', 'activex', 'externallinks')):
                raise ValueError('Macros, objetos ativos e referências externas não são permitidos.')
            if name.endswith('.svg'):
                raise ValueError('SVG incorporado requer conversão prévia para PDF ou imagem raster segura.')
            if name.endswith(('.xml', '.rels')):
                xml = archive.read(entry)
                node = ElementTree.fromstring(xml)
                for element in node.iter():
                    tag = element.tag.rsplit('}', 1)[-1].lower()
                    attributes = str(element.attrib).lower()
                    if tag.startswith('dde') or any(marker in attributes for marker in ('macroenabled','vbaproject','.macrosheet','/activex','/oleobject')):
                        raise ValueError('Conteúdo ativo não permitido.')
                    if re.search(r'(?i)\bDDE(?:AUTO)?\s', element.text or ''):
                        raise ValueError('Campos DDE não são permitidos.')
                if re.search(rb'(?i)(ddeauto|<\w*:?(?:dde|ddeLink)\b|macroEnabled|WEBSERVICE\s*\(|RTD\s*\()', xml):
                    raise ValueError('Conteúdo ativo não permitido.')
                if name.endswith('.rels'):
                    for relation in list(node):
                        if relation.get('TargetMode') == 'External':
                            if relation.get('Type', '').endswith('/attachedTemplate'):
                                if not relation.get('Target','').lower().endswith('.dotx'):
                                    raise ValueError('Template externo com formato ativo ou desconhecido não permitido.')
                                # Old Word templates often point to a workstation share.
                                # Never fetch it; embedded styles remain, report this limitation.
                                node.remove(relation)
                                replacements[entry.filename] = ElementTree.tostring(node)
                                warnings.append('Modelo externo do Word ignorado; apenas estilos incorporados foram utilizados.')
                                continue
                            if not relation.get('Type', '').endswith('/hyperlink') or not relation.get('Target', '').lower().startswith(('https://', 'http://', 'mailto:')):
                                raise ValueError('Recurso externo ativo não permitido.')
        if replacements:
            clean = io.BytesIO()
            with zipfile.ZipFile(clean, 'w', zipfile.ZIP_DEFLATED) as output:
                for entry in entries:
                    output.writestr(entry.filename, replacements.get(entry.filename, archive.read(entry)))
            path.write_bytes(clean.getvalue())
    return sorted(set(warnings))


def render(root):
    import pymupdf as fitz
    from PIL import Image, ImageOps
    source = next(root.glob('source.*'))
    suffix = source.suffix
    parts = []
    if suffix in ('.docx', '.xlsx', '.xls'):
        warnings = validate_office(source)
        warnings.append('Pré-visualização gerada: fontes e paginação podem diferir do aplicativo Office original.')
        helper = Path(__file__).with_name('uno_convert.py')
        uno_python = os.environ.get('LIBRARY_UNO_PYTHON', '/usr/bin/python3')
        uno_path = os.environ.get('LIBRARY_UNO_PATH', '/usr/lib/libreoffice/program')
        env = dict(os.environ)
        env['PYTHONPATH'] = uno_path + ':' + str(Path(uno_path).parents[1] / 'python3/dist-packages')
        env['LD_LIBRARY_PATH'] = uno_path + ':' + os.environ.get('LIBRARY_OFFICE_LD_PATH', '')
        env['URE_BOOTSTRAP'] = 'vnd.sun.star.pathname:' + str(Path(uno_path) / 'fundamentalrc')
        env['UNO_TYPES'] = ' '.join((Path(uno_path) / p).as_uri() for p in ('types.rdb', 'types/offapi.rdb'))
        env['UNO_SERVICES'] = ' '.join((Path(uno_path) / p).as_uri() for p in ('services.rdb', 'services/services.rdb'))
        subprocess.run([uno_python, str(helper), str(source)], env=env, check=True, timeout=85)
        parts = json.loads((root / 'office-parts.json').read_text())
    elif suffix == '.pdf':
        if not source.read_bytes().startswith(b'%PDF-'):
            raise ValueError('Conteúdo não corresponde a PDF.')
        parts = [{'name': 'Documento', 'file': source.name}]
    else:
        Image.MAX_IMAGE_PIXELS = 32_000_000
        with Image.open(source) as image:
            if image.format != ('PNG' if suffix == '.png' else 'JPEG'):
                raise ValueError('Conteúdo não corresponde à imagem declarada.')
            image.load()
            image = ImageOps.exif_transpose(image)
            matte = Image.new('RGBA', image.size, 'white')
            matte.alpha_composite(image.convert('RGBA'))
            image = matte.convert('RGB')
            image.info.clear()
            if image.width * image.height > 32_000_000:
                raise ValueError('Imagem excede o limite de pixels.')
            image.save(root / 'page-0-0.png')
            return {'parts': [{'index': 0, 'name': 'Imagem', 'pages': [{'index': 0, 'width': image.width, 'height': image.height}]}], 'renderer': 'safe-raster-v1'}
    manifest = {'parts': [], 'renderer': 'libreoffice-pymupdf-raster-v1' if suffix != '.pdf' else 'pymupdf-raster-v1', 'warnings': warnings if suffix != '.pdf' else []}
    count = 0
    stored_bytes = 0
    for index, part in enumerate(parts):
        with fitz.open(root / part['file']) as pdf:
            if pdf.needs_pass or not pdf.page_count:
                raise ValueError('PDF cifrado ou sem páginas.')
            for xref in range(1, pdf.xref_length()):
                obj = pdf.xref_object(xref)
                if re.search(r'/(JavaScript|JS|Launch|EmbeddedFile|RichMedia|XFA)\b', obj):
                    raise ValueError('Conteúdo ativo de PDF não permitido.')
            info = {'index': index, 'name': part['name'], 'pages': []}
            for page_index, page in enumerate(pdf):
                count += 1
                if count > 160 or page.rect.width * page.rect.height * 16 > 32_000_000:
                    raise ValueError('Documento excede os limites de páginas ou pixels.')
                pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), alpha=False)
                output = root / f'page-{index}-{page_index}.png'
                pix.save(output)
                stored_bytes += output.stat().st_size
                if stored_bytes > 96 * 1024**2:
                    raise ValueError('Pré-visualização excede o limite de armazenamento.')
                info['pages'].append({'index': page_index, 'width': pix.width, 'height': pix.height})
            manifest['parts'].append(info)
    if not manifest['parts']:
        raise ValueError('Documento sem conteúdo visível.')
    return manifest


if __name__ == '__main__':
    directory = Path(sys.argv[1]).resolve()
    try:
        offline_sandbox()
        result = render(directory)
        (directory / 'manifest.json').write_text(json.dumps(result))
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else 'Conversão segura falhou; publicação não permitida. Verifique o formato e a infraestrutura.'
        (directory / 'error.json').write_text(json.dumps({'error': message}))
        sys.exit(1)
