#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from epi_backend.manufacture_date_ocr import get_ocr_runtime_status


def env_truthy(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name, '')).strip().lower()
    if not raw:
        return default
    return raw in {'1', 'true', 'yes', 'on'}


def parse_args():
    parser = argparse.ArgumentParser(description='Valida runtime de OCR (Tesseract + pytesseract).')
    parser.add_argument(
        '--require',
        action='store_true',
        help='Força falha (exit 1) se OCR não estiver pronto.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Imprime saída em JSON.',
    )
    parser.add_argument(
        '--allow-missing-local',
        action='store_true',
        help='Em ambiente local, não falha quando OCR estiver ausente.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    running_on_render = bool(os.environ.get('RENDER'))
    env_mode = 'render' if running_on_render else 'local'
    require_ocr = bool(
        args.require
        or env_truthy('OCR_REQUIRED', default=running_on_render)
    )
    if args.allow_missing_local and not running_on_render:
        require_ocr = False
    which_tesseract = shutil.which('tesseract') or ''
    cli_version = ''
    if which_tesseract:
        try:
            proc = subprocess.run(
                [which_tesseract, '--version'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            cli_version = str(proc.stdout or proc.stderr).splitlines()[0]
        except Exception as exc:
            cli_version = f'erro: {exc}'

    status = get_ocr_runtime_status()
    payload = {
        'environment': env_mode,
        'require_ocr': require_ocr,
        'running_on_render': running_on_render,
        'which_tesseract': which_tesseract,
        'tesseract_version_cli_direct': cli_version,
        'runtime': status,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print('environment:', payload['environment'])
        print('require_ocr:', payload['require_ocr'])
        print('running_on_render:', payload['running_on_render'])
        print('which_tesseract:', payload['which_tesseract'])
        print('tesseract_version_cli_direct:', payload['tesseract_version_cli_direct'])
        print('python_dependencies_ready:', status.get('python_dependencies_ready'))
        print('tesseract_cmd:', status.get('tesseract_cmd'))
        print('tesseract_in_path:', status.get('tesseract_in_path'))
        print('tesseract_version_cli:', status.get('tesseract_version_cli'))
        print('tesseract_version_python:', status.get('tesseract_version_python'))
        print('ready:', status.get('ready'))

    if require_ocr and not status.get('ready'):
        raise SystemExit(
            'OCR obrigatório e indisponível. '
            f"Erro: {status.get('error')} | which tesseract: {which_tesseract or 'não encontrado'}"
        )
    if not require_ocr and not status.get('ready'):
        print(
            f"[WARN] OCR opcional indisponível ({env_mode}). "
            f"Isto é esperado em desenvolvimento local sem OCR. Motivo: {status.get('error')}"
        )


if __name__ == '__main__':
    main()
