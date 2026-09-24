from __future__ import annotations

import pytest
import requests

from agents.research.connectors.brave.config import BRAVE_SEARCH_BASE_URL
from agents.research.connectors.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from agents.research.connectors.serp.base import validate_serp_response
from agents.research.connectors.serp.provider import get_provider

class FakeResponse:
    def __init__(self, payload, *, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

class FakeSession:
    def __init__(self, response=None, responses=None):
        self.responses = list(responses or ([] if response is None else [response]))
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError('unexpected Brave Search request')
        return self.responses.pop(0)

VALID_PAYLOAD = {
    'type': 'search',
    'web': {
        'results': [
            {
                'title': 'Result One',
                'url': 'https://Example.com/page?utm_source=brave&ref=keep',
                'description': 'Description one',
            },
            {
                'title': 'Result Two',
                'url': 'https://example.org/other',
                'description': 'Description two',
            },
        ]
    },
}

def test_brave_factory_is_registered_but_not_default():
    assert get_provider('brave').provider_name == 'brave'

def test_brave_requires_api_key_before_network():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    session = FakeSession(response=FakeResponse(VALID_PAYLOAD))
    provider = BraveSERPProvider(session=session, api_key=None)
    with pytest.raises(ProviderConfigurationError):
        provider.get_results('expat health insurance', 'en', 'US')
    assert session.calls == []

def test_brave_normalizes_response_to_provider_order_and_url():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    session = FakeSession(response=FakeResponse(VALID_PAYLOAD))
    provider = BraveSERPProvider(session=session, api_key='test-key', count=2, offset=0)
    result = provider.get_results('expat health insurance', 'en', 'US')
    validate_serp_response(result, expected_provider='brave')
    assert result['provider'] == 'brave'
    assert result['position_semantics'] == 'provider_order'
    assert [item['position'] for item in result['results']] == [1, 2]
    assert result['results'][0]['url'] == 'https://Example.com/page?ref=keep'
    assert result['results'][0]['domain'] == 'example.com'
    assert 'google_rank' not in result
    assert 'rank_absolute' not in result['results'][0]

def test_brave_nullable_description_normalizes_to_empty_snippet():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider

    payload = {
        'web': {
            'results': [
                {
                    'title': 'Result',
                    'url': 'https://example.com/page',
                    'description': None,
                }
            ]
        }
    }
    provider = BraveSERPProvider(
        session=FakeSession(response=FakeResponse(payload)),
        api_key='test-key',
    )

    result = provider.get_results('kw', 'en', 'US')
    assert result['results'][0]['snippet'] == ''

def test_brave_request_maps_country_language_count_offset_and_freshness():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    session = FakeSession(response=FakeResponse(VALID_PAYLOAD))
    provider = BraveSERPProvider(session=session, api_key='test-key', count=10, offset=1, freshness='pw', timeout_seconds=7)
    provider.get_results(' expat health insurance ', 'EN', 'us')
    url, kwargs = session.calls[0]
    assert url == BRAVE_SEARCH_BASE_URL
    assert kwargs['timeout'] == 7
    assert kwargs['headers']['X-Subscription-Token'] == 'test-key'
    assert kwargs['params'] == {'q': 'expat health insurance', 'country': 'US', 'search_lang': 'en', 'count': 10, 'offset': 1, 'freshness': 'pw'}

@pytest.mark.parametrize('count,offset,message', [(0,0,'count'), (21,0,'count'), (10,-1,'offset'), (10,10,'offset')])
def test_brave_pagination_limits_fail_closed(count, offset, message):
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    provider = BraveSERPProvider(session=FakeSession(response=FakeResponse(VALID_PAYLOAD)), api_key='test-key', count=count, offset=offset)
    with pytest.raises(ValueError, match=message):
        provider.get_results('kw', 'en', 'US')

@pytest.mark.parametrize('status', [401, 403])
def test_brave_authentication_errors_are_normalized(status):
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    provider = BraveSERPProvider(session=FakeSession(response=FakeResponse({}, status_code=status)), api_key='test-key')
    with pytest.raises(ProviderAuthenticationError):
        provider.get_results('kw', 'en', 'US')

def test_brave_rate_limit_error_is_normalized():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    provider = BraveSERPProvider(session=FakeSession(response=FakeResponse({}, status_code=429)), api_key='test-key')
    with pytest.raises(ProviderRateLimitError):
        provider.get_results('kw', 'en', 'US')

def test_brave_http_error_is_normalized():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    provider = BraveSERPProvider(session=FakeSession(response=FakeResponse({}, status_code=500)), api_key='test-key')
    with pytest.raises(ProviderResponseError, match='HTTP 500'):
        provider.get_results('kw', 'en', 'US')

def test_brave_timeout_is_normalized():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    class TimeoutSession:
        def get(self, url, **kwargs):
            raise requests.Timeout('timeout')
    provider = BraveSERPProvider(session=TimeoutSession(), api_key='test-key')
    with pytest.raises(ProviderNetworkError):
        provider.get_results('kw', 'en', 'US')

def test_brave_connection_error_is_normalized():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    class ConnectionSession:
        def get(self, url, **kwargs):
            raise requests.ConnectionError('connection')
    provider = BraveSERPProvider(session=ConnectionSession(), api_key='test-key')
    with pytest.raises(ProviderNetworkError):
        provider.get_results('kw', 'en', 'US')

def test_brave_invalid_json_is_normalized():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    class InvalidJsonResponse:
        status_code = 200
        def json(self):
            raise ValueError('invalid')
    provider = BraveSERPProvider(session=FakeSession(response=InvalidJsonResponse()), api_key='test-key')
    with pytest.raises(ProviderResponseError, match='invalid JSON'):
        provider.get_results('kw', 'en', 'US')

@pytest.mark.parametrize('payload,match', [
    ({'type': 'search'}, 'web result collection'),
    ({'web': {}}, 'web.results'),
    ({'web': {'results': 'bad'}}, 'web.results'),
    ({'web': {'results': [{'title': 'Title', 'url': 'not-a-url', 'description': 'Description'}]}}, 'hostname'),
])
def test_brave_malformed_payloads_fail_closed(payload, match):
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    provider = BraveSERPProvider(session=FakeSession(response=FakeResponse(payload)), api_key='test-key')
    with pytest.raises(ProviderResponseError, match=match):
        provider.get_results('kw', 'en', 'US')

def test_brave_empty_results_are_valid():
    from agents.research.connectors.serp.providers.brave import BraveSERPProvider
    provider = BraveSERPProvider(session=FakeSession(response=FakeResponse({'web': {'results': []}})), api_key='test-key')
    result = provider.get_results('kw', 'en', 'US')
    assert result['results'] == []
    assert result['position_semantics'] == 'provider_order'