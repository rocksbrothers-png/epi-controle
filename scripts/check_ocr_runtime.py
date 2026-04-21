#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from epi_backend.manufacture_date_ocr import get_ocr_runtime_status


def main():
    status = get_ocr_runtime_status()
    print('python_dependencies_ready:', status.get('python_dependencies_ready'))
    print('tesseract_cmd:', status.get('tesseract_cmd'))
    print('tesseract_in_path:', status.get('tesseract_in_path'))
    print('tesseract_version_cli:', status.get('tesseract_version_cli'))
    print('tesseract_version_python:', status.get('tesseract_version_python'))
    print('ready:', status.get('ready'))
    if not status.get('ready'):
        raise SystemExit(f"OCR runtime invalid: {status.get('error')}")


if __name__ == '__main__':
    main()
