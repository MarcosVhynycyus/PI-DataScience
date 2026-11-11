import ast
import contextlib
from contextlib import closing
import io
import json
import os
from pathlib import Path
import runpy
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

RENDERED = Path('/tmp/pi-monitoring-validation')


@unittest.skipUnless((RENDERED / 'dashboard.json').exists(), 'Execute monitoring/tests/render.yml primeiro')
class ConfigurationTests(unittest.TestCase):
    def test_provisioning_references_and_preservation(self):
        datasource = yaml.safe_load((RENDERED / 'datasource.yml').read_text())['datasources'][0]
        providers = yaml.safe_load((RENDERED / 'dashboards.yml').read_text())['providers']
        dashboard = json.loads((RENDERED / 'dashboard.json').read_text())
        compose = yaml.safe_load((RENDERED / 'compose.yml').read_text())
        self.assertFalse(datasource['isDefault'])
        self.assertEqual(datasource['jsonData']['timeInterval'], '15s')
        self.assertEqual(dashboard['refresh'], '15s')
        self.assertEqual(dashboard['title'], 'Monitoramento — VM Geradora')
        self.assertTrue(providers[0]['disableDeletion'])
        self.assertIn('grafana_data:/var/lib/grafana', compose['services']['grafana']['volumes'])
        ids = [p['id'] for p in dashboard['panels']]
        self.assertEqual(len(ids), len(set(ids)))
        for panel in dashboard['panels']:
            if panel['type'] != 'row':
                self.assertEqual(panel['datasource']['uid'], datasource['uid'])
        ast.parse((RENDERED / 'firewall.py').read_text())

    def test_existing_default_datasource_is_preserved(self):
        root = Path(__file__).resolve().parents[2]
        tasks = yaml.safe_load((root / 'infra/ansible/roles/grafana_provisioning/tasks/main.yml').read_text())
        script = tasks[1]['ansible.builtin.command']['argv'][2]
        import sqlite3
        with tempfile.TemporaryDirectory(prefix='pi-grafana-test-') as directory:
            database = Path(directory) / 'grafana.db'
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('CREATE TABLE data_source (org_id INTEGER, is_default INTEGER, uid TEXT)')
            for uid, expected in ((None, True), ('existing-datasource', False), ('vm-prometheus', True)):
                with closing(sqlite3.connect(database)) as db, db:
                    db.execute('DELETE FROM data_source')
                    if uid:
                        db.execute('INSERT INTO data_source VALUES (1, 1, ?)', (uid,))
                result = subprocess.run([sys.executable, '-c', script, directory, 'vm-prometheus'],
                                        text=True, capture_output=True, check=True)
                self.assertEqual(json.loads(result.stdout)['make_default'], expected)

    def test_promql_with_promtool_and_known_metric_values(self):
        promtool = os.getenv('PROMTOOL') or shutil.which('promtool')
        if not promtool:
            self.skipTest('Defina PROMTOOL para validar consultas e resultados PromQL')
        dashboard = json.loads((RENDERED / 'dashboard.json').read_text())
        rules = []
        by_title = {}
        for panel in dashboard['panels']:
            for target in panel.get('targets', []):
                expression = target['expr'].replace('$__rate_interval', '1m').replace('$instance', '.*').replace('$vm', '.*')
                rules.append({'record': 'dashboard_query_' + str(len(rules)), 'expr': expression})
                by_title[panel['title']] = expression
        rule_path = RENDERED / 'dashboard-rules.yml'
        rule_path.write_text(yaml.safe_dump({'groups': [{'name': 'dashboard', 'rules': rules}]}))
        subprocess.run([promtool, 'check', 'config', str(RENDERED / 'prometheus.yml')], check=True, capture_output=True)
        subprocess.run([promtool, 'check', 'rules', str(rule_path)], check=True, capture_output=True)
        labels = 'instance="generator:9100",job="vm-geradora",vm="generator"'
        inputs = [
            {'series': 'node_cpu_seconds_total{' + labels + ',mode="idle",cpu="0"}', 'values': '0+7.5x20'},
            {'series': 'node_memory_MemTotal_bytes{' + labels + '}', 'values': '1000+0x20'},
            {'series': 'node_memory_MemAvailable_bytes{' + labels + '}', 'values': '400+0x20'},
            {'series': 'node_time_seconds{' + labels + '}', 'values': '1000+0x20'},
            {'series': 'node_boot_time_seconds{' + labels + '}', 'values': '100+0x20'},
            {'series': 'node_filesystem_size_bytes{' + labels + ',fstype="ext4",mountpoint="/"}', 'values': '1000+0x20'},
            {'series': 'node_filesystem_avail_bytes{' + labels + ',fstype="ext4",mountpoint="/"}', 'values': '250+0x20'},
            {'series': 'up{' + labels + '}', 'values': '1 1 1 1 1 1 1 1 0'},
        ]
        cases = [
            ('CPU utilizada', '{instance="generator:9100",vm="generator"}', 50),
            ('RAM utilizada', '{' + labels + '}', 60),
            ('RAM utilizada em bytes', '{' + labels + '}', 600),
            ('RAM disponível', 'node_memory_MemAvailable_bytes{' + labels + '}', 400),
            ('Uptime', '{' + labels + '}', 900),
            ('Disco utilizado', '{' + labels + ',fstype="ext4",mountpoint="/"}', 75),
            ('Disponibilidade da VM', 'up{' + labels + '}', 0),
        ]
        test = {'rule_files': [], 'evaluation_interval': '15s', 'tests': [{
            'interval': '15s', 'input_series': inputs,
            'promql_expr_test': [{'expr': by_title[title], 'eval_time': '2m',
                                  'exp_samples': [{'labels': expected_labels, 'value': value}]}
                                 for title, expected_labels, value in cases],
        }]}
        test_path = RENDERED / 'promql-tests.yml'
        test_path.write_text(yaml.safe_dump(test))
        result = subprocess.run([promtool, 'test', 'rules', str(test_path)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class GrafanaProvisioningTests(unittest.TestCase):
    """Reproduz a mudança de armazenamento do Grafana com bancos SQLite reais."""
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        tasks = yaml.safe_load((root / 'infra/ansible/roles/grafana_provisioning/tasks/main.yml').read_text())
        task = next(item for item in tasks if item.get('register') == 'grafana_provisioning_loaded')
        self.script = task['ansible.builtin.command']['argv'][2]
        self.resource = ('dashboard.grafana.app', 'dashboards', 'default', 'vm-geradora')

    def verify(self, version, legacy_rows=(), resources=None, legacy_table=True, source=True):
        with tempfile.TemporaryDirectory(prefix='pi-grafana-provisioning-') as directory:
            database = Path(directory) / 'grafana.db'
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('CREATE TABLE data_source (org_id INTEGER, uid TEXT, url TEXT)')
                if source:
                    db.execute('INSERT INTO data_source VALUES (1, ?, ?)',
                               ('vm-prometheus', 'http://monitoring:9090'))
                if legacy_table:
                    db.execute('CREATE TABLE dashboard (org_id INTEGER, uid TEXT)')
                    db.executemany('INSERT INTO dashboard VALUES (?, ?)', legacy_rows)
                if resources is not None:
                    db.execute('CREATE TABLE resource ("group" TEXT, resource TEXT, namespace TEXT, name TEXT)')
                    db.executemany('INSERT INTO resource VALUES (?, ?, ?, ?)', resources)
            original = database.read_bytes()
            result = subprocess.run([sys.executable, '-c', self.script, directory,
                                     'vm-prometheus', 'http://monitoring:9090', version],
                                    text=True, capture_output=True)
            self.assertEqual(database.read_bytes(), original, 'A verificação deve somente ler o banco')
            return result

    def test_legacy_dashboard_is_found_in_grafana_12(self):
        result = self.verify('12.4.0', legacy_rows=[(1, 'vm-geradora')])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unified_dashboard_is_found_with_empty_or_removed_legacy_table(self):
        for version, legacy_table in [('13.3.1', True), ('13.3.1', False), ('12.4.0', True)]:
            with self.subTest(version=version, legacy_table=legacy_table):
                result = self.verify(version, resources=[self.resource], legacy_table=legacy_table)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_dashboard_still_fails_validation(self):
        for version in ['12.4.0', '13.3.1']:
            with self.subTest(version=version):
                result = self.verify(version, resources=[])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Dashboard ausente', result.stderr)

    def test_stale_legacy_dashboard_does_not_mask_missing_unified_dashboard(self):
        result = self.verify('13.3.1', legacy_rows=[(1, 'vm-geradora')], resources=[])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Dashboard ausente', result.stderr)

    def test_unrelated_resource_does_not_satisfy_dashboard_check(self):
        for index, value in [(0, 'folder.grafana.app'), (1, 'folders'),
                             (2, 'org-2'), (3, 'outro-dashboard')]:
            with self.subTest(field=index):
                unrelated = list(self.resource)
                unrelated[index] = value
                result = self.verify('13.3.1', resources=[unrelated])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Dashboard ausente', result.stderr)

    def test_missing_datasource_still_fails_validation(self):
        result = self.verify('13.3.1', resources=[self.resource], source=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Fonte ausente', result.stderr)


class FakeIptables:
    def __init__(self):
        self.chains = {'INPUT': [['-p', 'tcp', '--dport', '22', '-j', 'ACCEPT']], 'DOCKER': []}
        self.mutations = 0

    def __call__(self, argv, **kwargs):
        operation, chain, *args = argv[3:]
        if '-s' in args:
            i = args.index('-s') + 1
            if '/' not in args[i]:
                args[i] += '/32'
        if '-d' in args:
            i = args.index('-d') + 1
            if '/' not in args[i]:
                args[i] += '/32'
        rc, output = 0, ''
        if operation == '-S':
            if chain not in self.chains:
                rc = 1
            else:
                output = '\n'.join(shlex.join(['-A', chain] + rule) for rule in self.chains[chain])
        elif operation == '-C':
            rc = 0 if args in self.chains[chain] else 1
        else:
            self.mutations += 1
            if operation == '-N': self.chains[chain] = []
            elif operation == '-F': self.chains[chain] = []
            elif operation == '-A': self.chains[chain].append(args)
            elif operation == '-I': self.chains[chain].insert(int(args[0]) - 1, args[1:])
            elif operation == '-D': self.chains[chain].remove(args)
            else: raise AssertionError(operation)
        result = subprocess.CompletedProcess(argv, rc, stdout=output, stderr='')
        if kwargs.get('check') and rc:
            raise subprocess.CalledProcessError(rc, argv)
        return result


@unittest.skipUnless((RENDERED / 'firewall.py').exists(), 'Execute monitoring/tests/render.yml primeiro')
class FirewallTests(unittest.TestCase):
    def test_repeated_apply_preserves_unrelated_rules_and_makes_no_changes(self):
        fake = FakeIptables()
        with patch('subprocess.run', side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(RENDERED / 'firewall.py'))
            first_mutations = fake.mutations
            runpy.run_path(str(RENDERED / 'firewall.py'))
        self.assertEqual(fake.mutations, first_mutations)
        self.assertIn(['-p', 'tcp', '--dport', '22', '-j', 'ACCEPT'], fake.chains['INPUT'])
        self.assertEqual(fake.chains['DOCKER'], [])
        metrics = fake.chains['MR-VM-METRICS']
        self.assertEqual(metrics[0][-2:], ['-j', 'ACCEPT'])
        self.assertEqual(metrics[-1][-2:], ['-j', 'DROP'])


if __name__ == '__main__':
    unittest.main()
