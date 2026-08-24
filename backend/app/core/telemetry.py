import logging
import json
import time
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "trace_context"):
            log_record.update(record.trace_context)
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_telemetry():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
        
    root_logger.addHandler(handler)
    
    # Silence noisy third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

class MetricsRegistry:
    def __init__(self):
        self.counters = {
            "simulation_ticks": 0,
            "agent_decisions_success": 0,
            "agent_decisions_failed": 0,
            "agent_decisions_fallback": 0,
            "llm_calls": 0,
            "llm_failures": 0,
            "llm_tokens": 0,
            "events_emitted": 0,
            "actions_rejected": 0,
            "actions_executed": 0,
        }
        
        self.accumulators = {
            "llm_latency_sum": 0.0,
            "llm_latency_count": 0,
            "db_latency_sum": 0.0,
            "db_latency_count": 0,
            "memory_retrieval_latency_sum": 0.0,
            "memory_retrieval_latency_count": 0,
        }
        
        self.gauges = {
            "websocket_connections": 0,
            "estimated_cost_usd": 0.0
        }
        
        self.start_time = time.time()

    def inc_counter(self, name: str, value: int = 1):
        if name in self.counters:
            self.counters[name] += value
            
    def observe_latency(self, name: str, latency_ms: float):
        sum_key = f"{name}_sum"
        count_key = f"{name}_count"
        if sum_key in self.accumulators:
            self.accumulators[sum_key] += latency_ms
            self.accumulators[count_key] += 1
            
    def set_gauge(self, name: str, value: float):
        if name in self.gauges:
            self.gauges[name] = value

    def inc_gauge(self, name: str, value: float = 1.0):
        if name in self.gauges:
            self.gauges[name] += value
            
    def get_metrics(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        uptime = max(uptime, 0.001)
        
        metrics = {
            "uptime_seconds": uptime,
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "rates": {
                "simulation_ticks_per_sec": self.counters["simulation_ticks"] / uptime,
                "agent_decisions_per_sec": (self.counters["agent_decisions_success"] + self.counters["agent_decisions_fallback"]) / uptime,
                "events_per_tick": self.counters["events_emitted"] / max(self.counters["simulation_ticks"], 1)
            },
            "averages": {}
        }
        
        for metric in ["llm_latency", "db_latency", "memory_retrieval_latency"]:
            count = self.accumulators[f"{metric}_count"]
            sum_val = self.accumulators[f"{metric}_sum"]
            metrics["averages"][f"avg_{metric}_ms"] = (sum_val / count) if count > 0 else 0.0
            
        return metrics

metrics = MetricsRegistry()

class TraceLogger:
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        
    def info(self, msg: str, **trace_kwargs):
        self.logger.info(msg, extra={"trace_context": trace_kwargs})
        
    def error(self, msg: str, **trace_kwargs):
        self.logger.error(msg, extra={"trace_context": trace_kwargs})

    def warning(self, msg: str, **trace_kwargs):
        self.logger.warning(msg, extra={"trace_context": trace_kwargs})
