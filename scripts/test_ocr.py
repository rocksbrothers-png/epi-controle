#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from epi_backend.manufacture_date_ocr import get_ocr_runtime_status

print(get_ocr_runtime_status())
