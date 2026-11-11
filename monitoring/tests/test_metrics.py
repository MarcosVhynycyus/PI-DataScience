import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'simulator'))
from metrics import GeneratorMetrics


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.metrics = GeneratorMetrics()

    def sample(self, name, labels=None):
        return self.metrics.registry.get_sample_value(name, labels or {})

    def test_counts_only_confirmed_records_and_resets_on_restart(self):
        self.metrics.record_written('vendas', 7)
        self.metrics.record_written('vendas', 3)
        self.assertEqual(self.sample('simulator_records_generated_total', {'table': 'vendas'}), 10)
        fresh = GeneratorMetrics()
        self.assertEqual(fresh.registry.get_sample_value('simulator_records_generated_total', {'table': 'vendas'}), 0)

    def test_error_and_recovery_preserve_last_success(self):
        self.metrics.cycle_succeeded(12, 0.25)
        last_success = self.sample('simulator_last_success_timestamp_seconds')
        self.metrics.failed('cycle')
        self.assertEqual(self.sample('simulator_ready'), 0)
        self.assertEqual(self.sample('simulator_generation_errors_total', {'stage': 'cycle'}), 1)
        self.assertEqual(self.sample('simulator_last_success_timestamp_seconds'), last_success)
        self.metrics.cycle_succeeded(5, 0.75)
        self.assertEqual(self.sample('simulator_ready'), 1)
        self.assertEqual(self.sample('simulator_generation_cycles_total'), 2)
        self.assertEqual(self.sample('simulator_last_batch_sales'), 5)
        self.assertEqual(self.sample('simulator_generation_cycle_duration_seconds_sum'), 1)

    def test_endpoint_is_opt_in(self):
        with patch.dict(os.environ, {'METRICS_ENABLED': 'false'}):
            self.assertIsNone(self.metrics.start_server())

    def test_numeric_values_are_observed_without_mutating_sales(self):
        sales = {'valor_total': [10.5, 20, float('nan'), 'R$ 8,00']}
        amount = self.metrics.sales_value_before_noise(sales)
        self.assertEqual(amount, 30.5)
        self.assertEqual(sales['valor_total'][3], 'R$ 8,00')
        self.metrics.cycle_succeeded(4, 0.1, amount)
        self.assertEqual(self.sample('simulator_last_batch_sales_value_brl'), 30.5)
        self.assertIsNone(self.metrics.sales_value_before_noise({}))

    def test_invalid_port_does_not_interrupt_generation(self):
        with patch.dict(os.environ, {'METRICS_ENABLED': 'true', 'METRICS_PORT': 'invalid'}):
            with self.assertLogs('metrics', level='ERROR'):
                self.assertIsNone(self.metrics.start_server())
        self.metrics.record_written('vendas', 1)
        self.assertEqual(self.sample('simulator_records_generated_total', {'table': 'vendas'}), 1)

    def start_endpoint(self, source):
        with patch.dict(os.environ, {'METRICS_ENABLED': 'true', 'METRICS_BIND_ADDRESS': '127.0.0.1',
                                    'METRICS_PORT': '0', 'METRICS_ALLOWED_SOURCES': source}):
            server = self.metrics.start_server()
        self.assertIsNotNone(server)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return 'http://127.0.0.1:' + str(server.server_port)

    def test_http_metrics_and_unknown_path(self):
        url = self.start_endpoint('127.0.0.1/32')
        with urlopen(url + '/metrics', timeout=3) as response:
            self.assertIn(b'simulator_records_generated_total{table="vendas"} 0.0', response.read())
        with self.assertRaises(HTTPError) as error:
            urlopen(url + '/', timeout=3)
        self.assertEqual(error.exception.code, 404)
        error.exception.close()

    def test_http_denies_unlisted_sources(self):
        url = self.start_endpoint('192.0.2.10/32')
        with self.assertRaises(HTTPError) as error:
            urlopen(url + '/metrics', timeout=3)
        self.assertEqual(error.exception.code, 403)
        error.exception.close()


class GeneratorIntegrationTests(unittest.TestCase):
    """Exercita o laço real sem banco, Docker ou alteração dos dados simulados."""
    def load_generator(self):
        fake_sqlalchemy = types.ModuleType('sqlalchemy')
        fake_sqlalchemy.text = lambda value: value
        fake_database = types.ModuleType('database')
        fake_database.engine = MagicMock()
        fake_pandas = types.ModuleType('pandas')
        fake_pandas.read_sql = MagicMock()
        fake_generator = types.ModuleType('gerador')
        for name in ('gerar_clientes', 'gerar_vendedores', 'gerar_estoque', 'gerar_vendas',
                     'gerar_crediario', 'gerar_promocoes', 'sujar_clientes', 'sujar_estoque',
                     'sujar_vendas', 'sujar_crediario', 'sujar_promocoes'):
            setattr(fake_generator, name, MagicMock())
        with patch.dict(sys.modules, {'sqlalchemy': fake_sqlalchemy, 'database': fake_database, 'pandas': fake_pandas,
                                      'gerador': fake_generator}):
            spec = importlib.util.spec_from_file_location('tested_stream_generator', ROOT / 'simulator/stream_generator.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module

    def run_cycle(self, failure=False):
        module = self.load_generator()
        sales, credit, promotions = MagicMock(), MagicMock(), MagicMock()
        sales.__len__.return_value = 8
        credit.__len__.return_value = 2
        promotions.__len__.return_value = 1
        credit.empty = False
        if failure:
            credit.to_sql.side_effect = RuntimeError('SQL indisponível')
        clients = MagicMock()
        clients.__getitem__.return_value.dropna.return_value.tolist.return_value = [1]
        with patch.object(module, 'parse_args'), patch.object(module, 'inicializar_dimensoes'), \
             patch.object(module.pd, 'read_sql', return_value=clients), \
             patch.object(module, 'gerar_vendas', return_value=sales), \
             patch.object(module, 'gerar_crediario', return_value=credit), \
             patch.object(module, 'gerar_promocoes', return_value=promotions), \
             patch.object(module, 'sujar_vendas', return_value=sales), \
             patch.object(module, 'sujar_crediario', return_value=credit), \
             patch.object(module, 'sujar_promocoes', return_value=promotions), \
             patch.object(module.time, 'sleep', side_effect=KeyboardInterrupt) as sleep, \
             patch.dict(os.environ, {'METRICS_ENABLED': 'false'}), patch('builtins.print'):
            with self.assertRaises(KeyboardInterrupt):
                module.rodar_simulador()
            sleep.assert_called_once_with(5)
        return module.metrics.registry, promotions

    def test_successful_cycle_keeps_writes_and_pause(self):
        registry, promotions = self.run_cycle()
        self.assertEqual(registry.get_sample_value('simulator_records_generated_total', {'table': 'vendas'}), 8)
        self.assertEqual(registry.get_sample_value('simulator_records_generated_total', {'table': 'crediario'}), 2)
        self.assertEqual(registry.get_sample_value('simulator_generation_cycles_total'), 1)
        promotions.to_sql.assert_called_once()

    def test_partial_failure_counts_only_committed_tables(self):
        registry, promotions = self.run_cycle(failure=True)
        self.assertEqual(registry.get_sample_value('simulator_records_generated_total', {'table': 'vendas'}), 8)
        self.assertEqual(registry.get_sample_value('simulator_records_generated_total', {'table': 'crediario'}), 0)
        self.assertEqual(registry.get_sample_value('simulator_generation_cycles_total'), 0)
        self.assertEqual(registry.get_sample_value('simulator_generation_errors_total', {'stage': 'cycle'}), 1)
        self.assertEqual(registry.get_sample_value('simulator_ready'), 0)
        promotions.to_sql.assert_not_called()


if __name__ == '__main__':
    unittest.main()
