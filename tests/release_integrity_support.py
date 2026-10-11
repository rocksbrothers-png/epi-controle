"""Execute release contract probes without SDKs, signing, credentials or uploads.

YAML is parsed as data, not matched by words in comments. Shell/Ruby command
boundaries run with instrumented test runners and Flutter. The guard itself
runs normally against the checkout under test. No repository file is edited.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

TEST_NAMES = ('test_api_backend_guard.py', 'test_flutter_release_api_base_url.py')
ROOT = pathlib.Path(__file__).resolve().parents[1]
PROOF_URL = 'https://validated-output.invalid/unique-proof'


def workflow(path):
    try:
        import yaml
    except ImportError as exc:
        raise AssertionError('Install ci/requirements-release.txt before release contract checks') from exc

    class UniqueLoader(yaml.BaseLoader):
        def construct_mapping(self, node, deep=False):
            pairs = self.construct_pairs(node, deep=deep)
            keys = [k for k, _ in pairs]
            assert len(keys) == len(set(keys)), f'{path}: duplicate YAML mapping keys'
            return dict(pairs)

    assert path.exists(), f'Workflow missing: {path}'
    data = yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)
    assert isinstance(data, dict) and isinstance(data.get('jobs'), dict), path
    return data


def unconditional(obj, context):
    assert 'if' not in obj, f'{context}: conditional integrity execution'
    assert obj.get('continue-on-error', 'false') == 'false', f'{context}: failure tolerated'
    assert obj.get('shell', 'bash') == 'bash', f'{context}: unsupported failure semantics'


def environment(directory):
    # Inherit only toolchain routing; never pass signing or application secrets.
    env = {'PATH': str(directory / 'bin') + os.pathsep + os.defpath,
           'GITHUB_WORKSPACE': str(ROOT), 'GITHUB_OUTPUT': str(directory / 'output'),
           'TRACE': str(directory / 'trace'), 'ARGS_FILE': str(directory / 'args')}
    for name in ('RUBYLIB', 'LD_LIBRARY_PATH'):
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!{sys.executable}\n' + body, encoding='utf-8')
    path.chmod(0o755)


def shell(script, directory, env):
    result = subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', script],
                            cwd=directory, env=env, text=True, capture_output=True, timeout=20)
    return result


def gate_probe(script):
    for fail in ('', *TEST_NAMES):
        with tempfile.TemporaryDirectory(prefix='release-gate-') as temporary:
            directory = pathlib.Path(temporary)
            env = environment(directory)
            env['FAIL_TEST'] = fail
            executable(directory / 'bin/python3', '''import os,pathlib,sys
a=sys.argv[1:]
target=pathlib.Path(a[-1]).resolve() if a else pathlib.Path('/')
allowed=[pathlib.Path(os.environ['GITHUB_WORKSPACE'])/'tests'/n for n in
         ('test_api_backend_guard.py','test_flutter_release_api_base_url.py')]
if len(a)!=2 or a[0]!='-I' or target not in allowed: sys.exit(94)
with open(os.environ['TRACE'],'a') as f: f.write(target.name+'\\n')
sys.exit(38 if target.name==os.environ['FAIL_TEST'] else 0)
''')
            # Gate commands resolve relative to the same checkout as the build.
            result = shell('cd "$GITHUB_WORKSPACE"\n' + script, directory, env)
            trace = (directory / 'trace').read_text().splitlines() if (directory / 'trace').exists() else []
            expected = list(TEST_NAMES) if fail != TEST_NAMES[0] else [TEST_NAMES[0]]
            assert trace == expected, f'Gate did not execute expected tests: {trace}; {result.stderr}'
            assert (result.returncode != 0) == bool(fail), f'Gate swallowed failure of {fail}'


def gate_steps(data, job):
    steps = job.get('steps', [])
    assert isinstance(steps, list), 'Invalid steps'
    defaults = dict(data.get('defaults', {}).get('run', {}))
    defaults.update(job.get('defaults', {}).get('run', {}))
    candidates = []
    for index, step in enumerate(steps):
        if any(name in step.get('run', '') for name in TEST_NAMES):
            unconditional(step, 'gate step')
            assert not step.get('env'), 'Gate env can alter test execution'
            assert step.get('shell', defaults.get('shell', 'bash')) == 'bash', 'Gate shell can tolerate errors'
            working = step.get('working-directory', defaults.get('working-directory'))
            assert working in (None, '${{ github.workspace }}'), 'Gate is not testing the build checkout'
            candidates.append((index, step['run']))
    assert candidates, 'Executable pre-build integrity gate missing'
    gate_probe('\n'.join(s for _, s in candidates))
    return candidates


def checkout_contract(job):
    steps = job.get('steps', [])
    checkouts = [(i, s) for i, s in enumerate(steps) if str(s.get('uses', '')).startswith('actions/checkout@')]
    assert checkouts and checkouts[0][0] == 0, 'Checkout must precede integrity tests'
    for _, step in checkouts:
        unconditional(step, 'checkout')
        settings = step.get('with', {})
        assert settings.get('ref') in (None, '${{ github.sha }}'), 'Checkout ref differs from tested ref'
        assert 'path' not in settings, 'Checkout directory differs from tested directory'
    assert len(checkouts) == 1, 'A later checkout can replace the tested revision'


def always_on_contract():
    path = ROOT / '.github/workflows/backend-isolation.yml'
    data = workflow(path)
    events = data.get('on', {})
    assert isinstance(events, dict) and {'push', 'pull_request'} <= set(events), 'Integrity triggers missing'
    assert events['pull_request'] in ('', None, {}), 'PR integrity gate filtered or restricted'
    push = events['push'] or {}
    assert isinstance(push, dict) and set(push) <= {'branches'}, 'Push integrity gate filtered'
    assert 'branches' not in push or 'main' in push['branches'], 'main not covered'
    job = data['jobs'].get('integrity')
    assert isinstance(job, dict), 'Stable integrity job missing'
    unconditional(job, 'integrity job')
    assert not job.get('needs'), 'Integrity job depends on a conditional job'
    checkout_contract(job)
    gate_steps(data, job)


def expand_expressions(script, values):
    def replace(match):
        key = match.group(1).strip()
        assert key in values, f'Unverified release expression: {key}'
        return values[key]
    return re.sub(r'\$\{\{\s*(.*?)\s*\}\}', replace, script)


def resolver_probe(step):
    unconditional(step, 'backend resolver')
    assert step.get('env') == {'API_BASE_URL_INPUT': '${{ vars.API_BASE_URL }}'}, 'Backend owner/input changed'
    own = json.loads((ROOT / 'ci/authorized_backend.json').read_text())['api_base_url']
    other = ('https://epi-controle-app-gupy.onrender.com' if 'livamobile' in own
             else 'https://epi-controle-app-livamobile-api.onrender.com')
    for value, accepted in ((own, True), ('', False), ('   ', False), (other.upper().replace('HTTPS:', 'https:'), False)):
        with tempfile.TemporaryDirectory(prefix='release-resolve-') as temporary:
            directory = pathlib.Path(temporary)
            env = environment(directory)
            (directory / 'bin').mkdir()
            (directory / 'bin/python3').symlink_to(sys.executable)
            env['API_BASE_URL_INPUT'] = value
            result = shell(step['run'], directory, env)
            output = (directory / 'output').read_text().splitlines() if (directory / 'output').exists() else []
            assert (result.returncode == 0) == accepted, f'Resolver fail-closed broken: {value}; {result.stderr}'
            assert output == (['url=' + own] if accepted else []), f'Unvalidated output published: {output}'


def validated_build_arguments(args):
    """Read all Flutter define spellings, preserving duplicates and order."""
    assert args[:2] in (['build', 'ipa'], ['build', 'appbundle']) and '--release' in args, args
    defines = []
    index = 2
    while index < len(args):
        arg = args[index]
        assert not arg.startswith('--dart-define-from-file'), 'Unverified define file can override the backend'
        if arg in ('--dart-define', '--dart-defines', '-D'):
            index += 1
            assert index < len(args), 'Missing dart-define value'
            value = args[index]
        elif arg.startswith(('--dart-define=', '--dart-defines=')):
            value = arg.split('=', 1)[1]
        elif arg.startswith('-D'):
            value = arg[2:].removeprefix('=')
        else:
            index += 1
            continue
        # Flutter uses splitCommas:false: commas are part of the define value.
        if value.startswith('API_BASE_URL='):
            defines.append(value)
        index += 1
    assert defines == ['API_BASE_URL=' + PROOF_URL], f'Build bypassed validated output: {defines}'


def build_probe(step):
    unconditional(step, 'native build')
    assert not step.get('env'), 'Unverified build environment can override the backend'
    script = expand_expressions(step['run'], {'steps.backend.outputs.url': PROOF_URL,
                                 'steps.version.outputs.build_name': '1', 'steps.version.outputs.build_number': '1'})
    # The supported publication contract consumes validated step outputs directly.
    # Scrubbing a runtime variable would test its fallback instead of its real value.
    assert not re.search(r'\$(?:[A-Za-z_]|\{|\()', script), 'Unverified shell expansion in native build'
    with tempfile.TemporaryDirectory(prefix='release-build-') as temporary:
        directory = pathlib.Path(temporary)
        env = environment(directory)
        executable(directory / 'bin/flutter', '''import json,os,sys
with open(os.environ['ARGS_FILE'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
''')
        result = shell(script, directory, env)
        assert result.returncode == 0, f'Build command probe failed: {result.stderr}'
        assert (directory / 'args').exists(), 'No actual Flutter invocation'
        invocations = [json.loads(line) for line in (directory / 'args').read_text().splitlines()]
        for args in invocations:
            validated_build_arguments(args)


def publication_contracts():
    for path in sorted((ROOT / '.github/workflows').glob('*')):
        if path.suffix not in ('.yml', '.yaml'):
            continue
        data = workflow(path)
        for job in data['jobs'].values():
            steps = job.get('steps', [])
            builds = []
            for index, step in enumerate(steps):
                # Never classify a whole shell block by a flag on another command.
                # Every direct appbundle/ipa build enters the contract, including
                # builds relying on Flutter's default mode or passing no-codesign.
                script = step.get('run', '').replace('\\\n', '')
                lexer = shlex.shlex(script, posix=True, punctuation_chars=';&|<>()')
                lexer.whitespace_split = True
                tokens = list(lexer)
                native = any(tokens[i:i + 3] in (['flutter', 'build', 'ipa'], ['flutter', 'build', 'appbundle'])
                             for i in range(len(tokens)))
                if native:
                    builds.append((index, step))
            if not builds:
                continue
            unconditional(job, f'{path.name} publisher')
            assert not data.get('env') and not job.get('env'), 'Unverified inherited publication environment'
            checkout_contract(job)
            gates = gate_steps(data, job)
            resolvers = [(i, s) for i, s in enumerate(steps) if s.get('id') == 'backend']
            assert len(resolvers) == 1, f'{path.name}: backend resolver missing/ambiguous'
            resolver_index, resolver = resolvers[0]
            assert max(i for i, _ in gates) < resolver_index < min(i for i, _ in builds), 'Gate/resolver not before build'
            resolver_probe(resolver)
            for _, step in builds:
                build_probe(step)


RUBY_PROBE = r'''
require 'json'
require 'shellwords'
$events = []
$lanes = {}
$probe_config = ENV.to_h
class ContractEnvironment
  ALLOWED = ['API_BASE_URL', 'APP_STORE_CONNECT_API_KEY_ID',
             'APP_STORE_CONNECT_API_ISSUER_ID', 'APP_STORE_CONNECT_API_KEY_BASE64'].freeze
  def initialize(values); @values = values; end
  def [](name)
    raise 'Unverified Fastlane environment: ' + name.to_s unless ALLOWED.include?(name)
    @values[name]
  end
  def fetch(name, *defaults, &block)
    self[name]
    @values.fetch(name, *defaults, &block)
  end
end
Object.send(:remove_const, :ENV)
Object.const_set(:ENV, ContractEnvironment.new($probe_config))
def default_platform(*); end
def desc(*); end
def platform(*); yield; end
def lane(name, &body)
  $lanes[name] = body
  define_singleton_method(name, &body)
end
module UI
  def self.user_error!(text); raise StandardError, text; end
end
def app_store_connect_api_key(*); $events << 'credentials'; end
def upload_to_testflight(*); $events << 'upload:testflight'; end
def sh(command)
  raise 'Unverified Fastlane shell operators/expansion' if command.match?(/[;$`|&<>\n]/)
  args = Shellwords.split(command)
  if args[0] == 'python3' && args[1] == '-I'
    allowed = ['test_api_backend_guard.py', 'test_flutter_release_api_base_url.py']
    name = File.basename(args[2].to_s)
    raise 'Wrong test checkout' unless args.length == 3 && allowed.include?(name) && args[2] == File.join(REPO_ROOT, 'tests', name)
    $events << 'gate:' + name
    raise 'Simulated failing integrity test' if name == $probe_config['FAIL_TEST']
  elsif args[0,2] == ['flutter','build']
    $events << args
  else
    raise 'Unexpected command: ' + command
  end
end
begin
  load ARGV.fetch(0)
  if $probe_config['RESOLVER_PROBE']
    $events << 'resolved:' + resolve_api_base_url!
  else
    # All filesystem effects remain in a disposable directory. REPO_ROOT stays
    # anchored to the checkout for guard and gate verification. The empty marker
    # is a test fixture only; no IPA is compiled, signed or uploaded.
    Object.send(:remove_const, :APP_ROOT)
    Object.const_set(:APP_ROOT, $probe_config.fetch('PROBE_APP_ROOT'))
    define_singleton_method(:prepare) { $events << 'prepare' }
    if $probe_config['PROOF_URL']
      define_singleton_method(:resolve_api_base_url!) { $probe_config['PROOF_URL'] }
    end
    send($probe_config.fetch('LANE'))
  end
rescue StandardError => e
  $events << 'error:' + e.message
end
puts JSON.generate($events)
'''


def fastlane_contract():
    ruby = os.environ.get('RELEASE_TEST_RUBY') or shutil.which('ruby')
    assert ruby, 'Ruby is required for the executable Fastlane integrity check'
    own = json.loads((ROOT / 'ci/authorized_backend.json').read_text())['api_base_url']
    file = ROOT / 'flutter/apps/epi_admin/ios/fastlane/Fastfile'
    other = ('https://epi-controle-app-gupy.onrender.com' if 'livamobile' in own
             else 'https://epi-controle-app-livamobile-api.onrender.com')
    # Execute the real Ruby resolver and Python guard before instrumenting the
    # lane's build boundary; an override alone would hide resolver regressions.
    for value, accepted in ((own, True), ('', False), ('   ', False), (other.upper().replace('HTTPS:', 'https:'), False)):
        with tempfile.TemporaryDirectory(prefix='fastlane-resolve-') as temporary:
            directory = pathlib.Path(temporary)
            env = environment(directory)
            (directory / 'bin').mkdir()
            (directory / 'bin/python3').symlink_to(sys.executable)
            env.update({'RESOLVER_PROBE': '1', 'API_BASE_URL': value})
            result = subprocess.run([ruby, '--disable-gems', '-e', RUBY_PROBE, str(file)],
                                    cwd=directory, env=env, text=True, capture_output=True, timeout=20)
            assert result.returncode == 0, f'Fastlane resolver probe error: {result.stderr}'
            events = json.loads(result.stdout)
            if accepted:
                assert events == ['resolved:' + own], events
            else:
                assert len(events) == 1 and events[0].startswith('error:'), f'Fastlane resolver accepted {value}: {events}'
    for lane in ('beta', 'release'):
        for fail in ('', *TEST_NAMES):
            with tempfile.TemporaryDirectory(prefix='release-fastlane-') as temporary:
                directory = pathlib.Path(temporary)
                env = environment(directory)
                artifact = directory / 'app/build/ios/ipa/probe.ipa'
                artifact.parent.mkdir(parents=True)
                artifact.touch()
                env.update({'LANE': lane, 'FAIL_TEST': fail, 'API_BASE_URL': own, 'PROOF_URL': PROOF_URL,
                            'PROBE_APP_ROOT': str(directory / 'app')})
                for key in ('APP_STORE_CONNECT_API_KEY_ID', 'APP_STORE_CONNECT_API_ISSUER_ID',
                            'APP_STORE_CONNECT_API_KEY_BASE64'):
                    env[key] = 'instrumented-signing-value'
                result = subprocess.run([ruby, '--disable-gems', '-e', RUBY_PROBE, str(file)],
                                        cwd=directory, env=env, text=True, capture_output=True, timeout=20)
                assert result.returncode == 0, f'Fastlane probe error: {result.stderr}'
                events = json.loads(result.stdout)
                prefix = ['gate:' + name for name in TEST_NAMES]
                if fail:
                    expected = prefix[:TEST_NAMES.index(fail) + 1]
                    assert events[:len(expected)] == expected, events
                    assert len(events) == len(expected) + 1 and str(events[-1]).startswith('error:'), events
                else:
                    assert events[:2] == prefix, f'Fastlane gate missing/late: {events}'
                    assert not any(isinstance(e, str) and e.startswith('error:') for e in events), events
                    builds = [e for e in events if isinstance(e, list)]
                    assert len(builds) == 1, events
                    validated_build_arguments(builds[0][1:])
                    assert events[-1] == 'upload:testflight' and events.count('upload:testflight') == 1, events
