"""Métricas do processo gerador; nenhuma consulta adicional ao banco de dados."""
import ipaddress
import logging
import math
from numbers import Real
import os
import threading
import time
from http.server import ThreadingHTTPServer

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, MetricsHandler

LOGGER = logging.getLogger(__name__)
TABLES = ("clientes", "vendedores", "estoque", "vendas", "crediario", "promocoes")


class GeneratorMetrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.records = Counter(
            "simulator_records_generated_total", "Registros gravados desde o início deste processo",
            ["table"], registry=self.registry,
        )
        for table in TABLES:
            self.records.labels(table=table)
        self.errors = Counter(
            "simulator_generation_errors_total", "Exceções operacionais; não inclui ruídos sintéticos",
            ["stage"], registry=self.registry,
        )
        for stage in ("initialization", "cycle"):
            self.errors.labels(stage=stage)
        self.cycles = Counter(
            "simulator_generation_cycles_total", "Ciclos concluídos com sucesso", registry=self.registry,
        )
        self.ready = Gauge(
            "simulator_ready", "1 após inicialização e último ciclo bem-sucedidos; 0 após erro",
            registry=self.registry,
        )
        self.last_success = Gauge(
            "simulator_last_success_timestamp_seconds", "Timestamp do último ciclo concluído",
            registry=self.registry,
        )
        self.batch_rows = Gauge(
            "simulator_last_batch_sales", "Vendas persistidas no último lote concluído",
            registry=self.registry,
        )
        self.batch_sales_value = Gauge(
            "simulator_last_batch_sales_value_brl", "Soma dos valores das vendas antes dos ruídos sintéticos",
            registry=self.registry,
        )
        self.duration = Histogram(
            "simulator_generation_cycle_duration_seconds", "Duração de cada ciclo, sem a pausa de 5s",
            registry=self.registry,
        )

    def start_server(self):
        """Falhas na exposição HTTP não interrompem a geração existente."""
        if os.getenv("METRICS_ENABLED", "false").lower() not in ("true", "1", "yes"):
            return None
        try:
            networks = [ipaddress.ip_network(value.strip(), strict=False)
                        for value in os.getenv("METRICS_ALLOWED_SOURCES", "127.0.0.1/32").split(",")
                        if value.strip()]
            if not networks:
                raise ValueError("METRICS_ALLOWED_SOURCES exige ao menos uma origem")
            base_handler = MetricsHandler.factory(self.registry)

            class AllowedMetricsHandler(base_handler):
                def do_GET(self):
                    address = ipaddress.ip_address(self.client_address[0])
                    if not any(address in network for network in networks):
                        self.send_error(403, "Origem não permitida")
                    elif self.path.split("?", 1)[0] != "/metrics":
                        self.send_error(404)
                    else:
                        super().do_GET()

            server = ThreadingHTTPServer(
                (os.getenv("METRICS_BIND_ADDRESS", "0.0.0.0"), int(os.getenv("METRICS_PORT", "8000"))),
                AllowedMetricsHandler,
            )
            threading.Thread(target=server.serve_forever, daemon=True).start()
            return server
        except Exception:
            LOGGER.exception("Endpoint de métricas indisponível; geração continuará")
            return None

    def record_written(self, table, count):
        self.records.labels(table=table).inc(count)

    @staticmethod
    def sales_value_before_noise(sales):
        try:
            return math.fsum(float(value) for value in sales['valor_total']
                             if isinstance(value, Real) and math.isfinite(value))
        except Exception:
            # Apenas a observação é descartada; nenhuma alteração no dataframe.
            return None

    def cycle_succeeded(self, sales, duration, sales_value=None):
        self.cycles.inc()
        self.batch_rows.set(sales)
        if sales_value is not None:
            self.batch_sales_value.set(sales_value)
        self.last_success.set(time.time())
        self.duration.observe(duration)
        self.ready.set(1)

    def failed(self, stage):
        self.errors.labels(stage=stage).inc()
        self.ready.set(0)
