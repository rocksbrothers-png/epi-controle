"""Trusted UNO controller. Document macros/updates never run. Unix pipe only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import uno


def prop(name, value):
    item = uno.createUnoStruct('com.sun.star.beans.PropertyValue')
    item.Name, item.Value = name, value
    return item


def convert(source):
    root = source.parent
    profile = root / 'profile'
    (profile / 'user').mkdir(parents=True)
    (profile / 'user/registrymodifications.xcu').write_text('''<?xml version="1.0"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item></oor:items>''')
    pipe = 'sst_' + uuid.uuid4().hex
    binary = os.environ.get('LIBRARY_SOFFICE', '/usr/lib/libreoffice/program/soffice')
    diagnostic = (root / 'converter.log').open('wb')
    office_env = dict(os.environ)
    office_env.pop('URE_BOOTSTRAP', None)
    process = subprocess.Popen([
        binary, '--headless', '--nologo', '--nodefault', '--norestore', '--nofirststartwizard',
        '-env:UserInstallation=' + profile.as_uri(),
        '-env:UNO_TYPES=' + os.environ['UNO_TYPES'],
        '-env:UNO_SERVICES=' + os.environ['UNO_SERVICES'],
        '--accept=pipe,name=' + pipe + ';urp;StarOffice.ComponentContext',
    ], env=office_env, stdout=subprocess.DEVNULL, stderr=diagnostic, close_fds=True)
    document = None
    try:
        context = uno.getComponentContext()
        resolver = context.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', context)
        remote = None
        for _ in range(120):
            if process.poll() is not None:
                raise ValueError('Conversor Office indisponível.')
            try:
                remote = resolver.resolve('uno:pipe,name=' + pipe + ';urp;StarOffice.ComponentContext')
                break
            except Exception:
                time.sleep(.1)
        if remote is None:
            raise ValueError('Conversor Office não respondeu.')
        desktop = remote.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', remote)
        document = desktop.loadComponentFromURL(source.as_uri(), '_blank', 0, (
            prop('Hidden', True), prop('ReadOnly', True),
            prop('MacroExecutionMode', uno.getConstantByName('com.sun.star.document.MacroExecMode.NEVER_EXECUTE')),
            prop('UpdateDocMode', uno.getConstantByName('com.sun.star.document.UpdateDocMode.NO_UPDATE')),
        ))
        if document is None:
            raise ValueError('Arquivo Office não pôde ser aberto com segurança.')
        parts = []
        if source.suffix in ('.xls', '.xlsx'):
            sheets = document.getSheets()
            visible = [sheets.getByIndex(i) for i in range(sheets.getCount()) if sheets.getByIndex(i).IsVisible]
            for index, selected in enumerate(visible):
                selected.IsVisible = True
                for i in range(sheets.getCount()):
                    other = sheets.getByIndex(i)
                    if other.Name != selected.Name:
                        other.IsVisible = False
                filename = f'part-{index}.pdf'
                document.storeToURL((root / filename).as_uri(), (prop('FilterName', 'calc_pdf_Export'), prop('Overwrite', True)))
                parts.append({'name': selected.Name, 'file': filename})
        else:
            document.storeToURL((root / 'part-0.pdf').as_uri(), (prop('FilterName', 'writer_pdf_Export'), prop('Overwrite', True)))
            parts.append({'name': 'Documento', 'file': 'part-0.pdf'})
        (root / 'office-parts.json').write_text(json.dumps(parts))
    finally:
        if document is not None:
            document.close(True)
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        diagnostic.close()


if __name__ == '__main__':
    convert(Path(sys.argv[1]).resolve())
