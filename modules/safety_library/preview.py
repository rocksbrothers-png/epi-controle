"""Convert untrusted uploads in a credential-free, offline, bounded worker.

Only rasterized pages leave this boundary. Never expose originals to employees.
Linux/libseccomp is mandatory: missing tooling fails closed, without publication.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PREVIEW_BYTES = 96 * 1024 * 1024
MIMES = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
}
_CONVERTER_SLOTS = threading.BoundedSemaphore(2)


def render_preview(content, filename, mime):
    if not _CONVERTER_SLOTS.acquire(blocking=False):
        raise ValueError('Conversor ocupado. Tente novamente em instantes.')
    try:
        return _render_preview(content, filename, mime)
    finally:
        _CONVERTER_SLOTS.release()


def _render_preview(content, filename, mime):
    extension = Path(filename).suffix.lower()
    if extension not in MIMES or mime != MIMES[extension]:
        raise ValueError('Extensão ou MIME não permitido.')
    if not content or len(content) > MAX_FILE_BYTES:
        raise ValueError('Arquivo vazio ou maior que 20 MiB.')
    # Deliberate whitelist; never inherit JWT/DB/cloud credentials or open fds.
    env = {key: os.environ[key] for key in (
        'PATH', 'LANG', 'LC_ALL', 'HOME', 'HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY',
        'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE',
        'LIBRARY_SOFFICE', 'LIBRARY_UNO_PYTHON', 'LIBRARY_UNO_PATH',
        'LIBRARY_OFFICE_LD_PATH', 'FONTCONFIG_FILE',
    ) if key in os.environ}
    env['GSETTINGS_BACKEND'] = 'memory'
    with tempfile.TemporaryDirectory(prefix='sst-preview-') as tmp:
        root = Path(tmp)
        source = root / ('source' + extension)
        source.write_bytes(content)
        env['TMPDIR'] = tmp
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name('render_worker.py')), tmp],
            env=env, cwd=tmp, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True, close_fds=True,
        )
        try:
            process.communicate(timeout=100)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ValueError('Pré-visualização excedeu o tempo permitido.') from None
        if process.returncode:
            error_file = root / 'error.json'
            message = json.loads(error_file.read_text())['error'] if error_file.exists() else 'Conversor seguro indisponível. Verifique a infraestrutura de pré-visualização.'
            # Do not reflect document content, filesystem paths or converter stderr.
            raise ValueError(message)
        manifest = json.loads((root / 'manifest.json').read_text())
        pages = []
        total = 0
        for part in manifest['parts']:
            for page in part['pages']:
                data = (root / f"page-{part['index']}-{page['index']}.png").read_bytes()
                total += len(data)
                if total > MAX_PREVIEW_BYTES:
                    raise ValueError('Pré-visualização excede o limite de armazenamento.')
                pages.append((part['index'], page['index'], data))
        return manifest, pages
