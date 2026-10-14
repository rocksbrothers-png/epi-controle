"""Mandatory non-DB tests: sandbox, malicious inputs and immutable SQLite history."""
import io
import sqlite3
import subprocess
import sys
import zipfile

import pytest

from core.auth import require_structural_admin
from modules.safety_library.preview import render_preview
from modules.safety_library.render_worker import validate_office
from modules.safety_library.schema import ensure_safety_library


def test_offline_worker_cannot_create_internet_socket():
    script="""from modules.safety_library.render_worker import offline_sandbox
import socket
offline_sandbox()
try: socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
except PermissionError: print('DENIED IPv6')
else: raise AssertionError('network permitted')
socket.socket(socket.AF_UNIX, socket.SOCK_STREAM).close()
"""
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert 'DENIED IPv6' in result.stdout


@pytest.mark.parametrize('role',['master_admin','admin','user','employee','buyer','approver','manager','safety_tech'])
def test_no_other_role_can_manage_even_with_generic_permissions(role):
    with pytest.raises(PermissionError):require_structural_admin({'role':role,'permissions':['safety_library:manage']})


def test_invalid_image_pdf_mime_and_size():
    for content,filename,mime in ((b'HTML','bad.pdf','application/pdf'),(b'PNG','bad.jpg','image/png'),(b'x'* (20*1024**2+1),'big.pdf','application/pdf')):
        with pytest.raises(ValueError):render_preview(content,filename,mime)


def test_image_preview_preserves_orientation_without_original_exif():
    from PIL import Image
    output=io.BytesIO()
    image=Image.new('RGB',(100,40),'green')
    exif=Image.Exif();exif[274]=6;exif[270]='Private original metadata'
    image.save(output,'JPEG',exif=exif)
    manifest,pages=render_preview(output.getvalue(),'photo.jpg','image/jpeg')
    rendered=Image.open(io.BytesIO(pages[0][2]))
    assert rendered.size==(40,100) and not rendered.getexif()
    assert b'Private original metadata' not in pages[0][2]
    assert manifest['parts'][0]['pages'][0]['width']==40


def test_transparent_image_is_readable_on_white_viewer_background():
    from PIL import Image
    output=io.BytesIO();image=Image.new('RGBA',(2,1),(0,0,0,0));image.putpixel((1,0),(255,0,0,255));image.save(output,'PNG')
    _,pages=render_preview(output.getvalue(),'diagram.png','image/png')
    rendered=Image.open(io.BytesIO(pages[0][2]))
    assert rendered.getpixel((0,0))==(255,255,255)
    assert rendered.getpixel((1,0))==(255,0,0)


@pytest.mark.parametrize('name,xml',[
    ('word/vbaProject.bin',b'hostile'),
    ('word/document.xml',b'<doc><instrText>DDEAUTO execute</instrText></doc>'),
    ('word/document.xml','<doc><instrText>DDE execute</instrText></doc>'.encode('utf-16')),
    ('word/_rels/document.xml.rels',b'<Relationships><Relationship TargetMode="External" Type="image" Target="https://attacker.invalid/x"/></Relationships>'),
    ('word/_rels/document.xml.rels',b'<Relationships><Relationship Type="http://schemas.microsoft.com/office/2006/relationships/vbaProject" Target="renamed.bin"/></Relationships>'),
    ('word/_rels/document.xml.rels',b'<Relationships><Relationship TargetMode="External" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" Target="file:///unsafe.dotm"/></Relationships>'),
    ('word/media/drawing.svg',b'<svg><script>active()</script></svg>'),
])
def test_active_office_is_rejected_before_converter(tmp_path,name,xml):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        z.writestr('[Content_Types].xml','<Types/>')
        if name!='word/document.xml':z.writestr('word/document.xml','<doc/>')
        z.writestr(name,xml)
    path=tmp_path/'source.docx';path.write_bytes(data.getvalue())
    with pytest.raises(ValueError):validate_office(path)


def test_zip_bomb_is_rejected_without_extracting(tmp_path):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types/>');z.writestr('word/document.xml',b'x'*1024*1024)
    path=tmp_path/'source.docx';path.write_bytes(output.getvalue())
    with pytest.raises(ValueError,match='comprimido'):validate_office(path)


def test_sqlite_model_idempotency_and_history_are_append_only():
    c=sqlite3.connect(':memory:');c.execute('PRAGMA foreign_keys=ON')
    for table in ('companies','users','employees','units'):c.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY)');c.execute(f'INSERT INTO {table} VALUES(1)')
    ensure_safety_library(c);ensure_safety_library(c)
    c.execute("INSERT INTO safety_document_audit(company_id,actor_user_id,action,decision,details,created_at) VALUES(1,1,'test','allow','{}','2026-01-01')")
    with pytest.raises(sqlite3.IntegrityError):c.execute("UPDATE safety_document_audit SET details='tampered'")
    with pytest.raises(sqlite3.IntegrityError):c.execute('DELETE FROM safety_document_audit')
    c.close()
