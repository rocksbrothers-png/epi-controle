"""Reproduce B01–B04 against real release contracts in disposable fixtures.

These are negative controls: baseline and restored configurations must pass,
while each syntactically valid release sabotage must raise a contract error.
No source checkout is mutated; no nested integrity test invokes this module.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = '.github/workflows/deploy-android.yml'
FASTFILE = 'flutter/apps/epi_admin/ios/fastlane/Fastfile'
DEFINE = '--dart-define=API_BASE_URL="${{ steps.backend.outputs.url }}"'


def fixture(directory):
    root = pathlib.Path(directory)
    shutil.copytree(ROOT / '.github/workflows', root / '.github/workflows')
    shutil.copytree(ROOT / 'ci', root / 'ci')
    for relative in (FASTFILE, 'tests/test_api_backend_guard.py', 'tests/test_flutter_release_api_base_url.py'):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    module = types.ModuleType('isolated_release_contract')
    source = ROOT / 'tests/release_integrity_support.py'
    module.__file__ = str(source)
    exec(compile(source.read_text(), str(source), 'exec'), module.__dict__)
    module.ROOT = root
    return root, module


def cross_tail(root):
    own = json.loads((root / 'ci/authorized_backend.json').read_text())['api_base_url']
    return 'gupy.onrender.com' if 'livamobile' in own else 'livamobile-api.onrender.com'


def replace_once(text, old, new):
    assert text.count(old) == 1, f'Regression fixture anchor changed: {old}'
    return text.replace(old, new, 1)


def rejected(contract, expected):
    try:
        contract()
    except AssertionError as exc:
        assert expected in str(exc), f'Sabotage failed for an unrelated reason: {exc}'
    else:
        raise AssertionError('Release sabotage escaped its executable contract')


def b01():
    with tempfile.TemporaryDirectory(prefix='regression-b01-') as temporary:
        root, contract = fixture(temporary)
        original = contract.workflow(root / WORKFLOW)['jobs']['deploy']['steps']
        step = next(s for s in original if s.get('name') == 'Build AAB (signed)')
        contract.build_probe(step)
        split = '"API_BASE_URL=https://epi-controle-app-""' + cross_tail(root) + '"'
        # The historical alias and conservative short-form inputs cannot evade counting.
        for option in ('--dart-define ', '--dart-defines ', '-D ', '-D', '--dart-defines='):
            changed = dict(step, run=replace_once(step['run'], DEFINE, DEFINE + ' \\\n  ' + option + split))
            rejected(lambda: contract.build_probe(changed), 'Build bypassed validated output')
        changed = dict(step, run=step['run'] + '\n')
        changed['run'] = replace_once(changed['run'], DEFINE, DEFINE + ' --dart-define-from-file=unverified.json')
        rejected(lambda: contract.build_probe(changed), 'Unverified define file')
        changed = dict(step, run=replace_once(step['run'], DEFINE, DEFINE + ',ignored'))
        rejected(lambda: contract.build_probe(changed), 'Build bypassed validated output')
        contract.build_probe(step)


def b02():
    with tempfile.TemporaryDirectory(prefix='regression-b02-') as temporary:
        root, contract = fixture(temporary)
        path = root / WORKFLOW
        original = path.read_text()
        contract.publication_contracts()
        start = original.index('      - name: Backend isolation integrity gate')
        stop = original.index('      - name:', start + 20)
        without_gate = original[:start] + original[stop:]
        split = '"https://epi-controle-app-""' + cross_tail(root) + '"'
        variants = [
            (without_gate, 'Executable pre-build integrity gate missing'),
            (original, 'Build bypassed validated output'),
        ]
        for command in ('flutter \\\n          build appbundle', ':;flutter build appbundle'):
            formatted = replace_once(original, 'flutter build appbundle', command)
            path.write_text(formatted)
            contract.publication_contracts()
            variants.append((replace_once(without_gate, 'flutter build appbundle', command),
                             'Executable pre-build integrity gate missing'))
        for source, expected in variants:
            changed = replace_once(source, DEFINE, '--dart-define=API_BASE_URL=' + split +
                                   "\n          printf '%s\\n' --no-codesign")
            path.write_text(changed)
            contract.workflow(path)  # YAML syntax validity is not the detector.
            rejected(contract.publication_contracts, expected)
        path.write_text(original)
        contract.publication_contracts()


def b03():
    with tempfile.TemporaryDirectory(prefix='regression-b03-') as temporary:
        root, contract = fixture(temporary)
        path = root / FASTFILE
        original = path.read_text()
        contract.fastlane_contract()
        second = ('    Dir.chdir(APP_ROOT) do\n'
                  '      sh("flutter build ipa --release --dart-define=API_BASE_URL=" +\n'
                  '         "https://epi-controle-app-" + "' + cross_tail(root) + '" +\n'
                  '         " --export-options-plist=ios/ExportOptions.plist")\n'
                  '    end\n')
        for anchor in ('    upload_to_testflight(', '    beta\n'):
            replacement = second + anchor if 'upload' in anchor else anchor + second
            path.write_text(replace_once(original, anchor, replacement))
            rejected(contract.fastlane_contract, 'flutter')
        changed = replace_once(original, 'sh("python3 -I #{t.shellescape}")',
                               'sh("python3 -I #{t.shellescape} || true")')
        path.write_text(changed)
        rejected(contract.fastlane_contract, 'Unverified Fastlane shell')
        path.write_text(original)
        contract.fastlane_contract()


def b04():
    with tempfile.TemporaryDirectory(prefix='regression-b04-') as temporary:
        root, contract = fixture(temporary)
        path = root / WORKFLOW
        original = path.read_text()
        contract.publication_contracts()
        fallback = replace_once(original, DEFINE,
                                '--dart-define=API_BASE_URL="${RELEASE_OVERRIDE:-${{ steps.backend.outputs.url }}}"')
        variants = [
            (replace_once(fallback, '- name: Build AAB (signed)',
                          '- name: Build AAB (signed)\n        env:\n          RELEASE_OVERRIDE: ${{ vars.UNVALIDATED_BACKEND }}'),
             'Unverified build environment'),
            (replace_once(fallback, '  deploy:\n', '  deploy:\n    env:\n      RELEASE_OVERRIDE: ${{ vars.UNVALIDATED_BACKEND }}\n'),
             'Unverified inherited publication environment'),
            ('env:\n  RELEASE_OVERRIDE: ${{ vars.UNVALIDATED_BACKEND }}\n' + fallback,
             'Unverified inherited publication environment'),
            (fallback, 'Unverified shell expansion'),
        ]
        for changed, expected in variants:
            path.write_text(changed)
            contract.workflow(path)
            rejected(contract.publication_contracts, expected)
        path.write_text(original)
        contract.publication_contracts()
        fastfile = root / FASTFILE
        original_fastfile = fastfile.read_text()
        contract.fastlane_contract()
        changed = replace_once(original_fastfile, '#{api_base_url.shellescape}',
                               "#{(ENV['RELEASE_OVERRIDE'] || api_base_url).shellescape}")
        fastfile.write_text(changed)
        rejected(contract.fastlane_contract, 'Unverified Fastlane environment')
        fastfile.write_text(original_fastfile)
        contract.fastlane_contract()
