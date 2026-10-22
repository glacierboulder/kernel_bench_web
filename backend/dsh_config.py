"""Trusted fixed-version headless configuration; never supplied by browser clients."""
import os
from .settings import SETTINGS

MODEL = 'deepseek-flash'
DEFAULT_CUMULATIVE_REQUEST_LIMIT = 500
REQUEST_LIMIT_ENV = 'BENCH_CUMULATIVE_REQUEST_LIMIT'
DEFAULT_MAX_OUTPUT_TOKENS = 32768

def output_token_limit(override=None):
    raw=override if override is not None else os.environ.get('BENCH_MAX_OUTPUT_TOKENS',DEFAULT_MAX_OUTPUT_TOKENS)
    value=int(raw)
    if not 1 <= value <= 393216:
        raise ValueError('BENCH_MAX_OUTPUT_TOKENS must be between 1 and 393216')
    return value



def cumulative_request_limit(override=None):
    """Return the paid model-request cap for one cumulative experiment chain.

    The default allows up to 500 requests. Operators can
    set ``BENCH_CUMULATIVE_REQUEST_LIMIT`` or pass the worker's
    ``--request-limit`` option; browser clients cannot change this value.
    """
    raw = override if override is not None else os.environ.get(
        REQUEST_LIMIT_ENV, str(DEFAULT_CUMULATIVE_REQUEST_LIMIT))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{REQUEST_LIMIT_ENV} must be a positive integer') from exc
    if value <= 0 or value > 10000:
        raise ValueError(f'{REQUEST_LIMIT_ENV} must be between 1 and 10000')
    return value

def patch_config(path, max_output_tokens=None):
    text='''- id: agent-default-model
  config:
    provider: deepseek-official
    model: deepseek-flash
- id: llm-deepseek
  config:
    baseURL: http://GATEWAY_HOST:GATEWAY_PORT/anthropic
    maxTokens: OUTPUT_TOKEN_LIMIT
    thinking: enabled
    reasoningEffort: high
- id: session-title-llm
  disabled: true
- id: web-search-deepseek
  disabled: true
- id: web-fetch-http
  disabled: true
- id: tool-subagent
  disabled: true
- id: tool-subagent-fork
  disabled: true
- id: tool-subagent-control
  disabled: true
- id: tool-subagent-list-agents
  disabled: true
- id: tool-plugin-manager
  disabled: true
- id: plugin-manager
  disabled: true
'''
    text=text.replace('OUTPUT_TOKEN_LIMIT',str(output_token_limit(max_output_tokens)))
    text=text.replace('GATEWAY_HOST',SETTINGS.gateway_host).replace('GATEWAY_PORT',str(SETTINGS.gateway_port))
    path.write_text(text)
