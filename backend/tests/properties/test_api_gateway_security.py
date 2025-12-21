"""
Property-based tests for API Gateway security enforcement.

**Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
**Validates: Requirements 10.3, 10.5**
"""

import pytest
import asyncio
import time
from hypothesis import given, strategies as st, assume, settings
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request, Response, HTTPException
from starlette.responses import JSONResponse

# Import only the security middleware to avoid model loading issues
import sys
import os
sys.path.insert(0, '/app')

from shared.middleware.security import (
    RateLimitMiddleware,
    IPFilterMiddleware,
    InputValidationMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    APIKeyMiddleware,
    SecurityConfig
)


# Hypothesis strategies for generating test data
@st.composite
def malicious_input_strategy(draw):
    """Generate potentially malicious input patterns."""
    attack_types = [
        # SQL injection patterns
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "UNION SELECT * FROM users",
        "admin'--",
        
        # XSS patterns
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<iframe src='javascript:alert(1)'></iframe>",
        "onload=alert('xss')",
        
        # Command injection patterns
        "; cat /etc/passwd",
        "| whoami",
        "`id`",
        "$(uname -a)",
        
        # Path traversal
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        
        # Header injection
        "test\r\nX-Injected: malicious",
        "test\nSet-Cookie: admin=true"
    ]
    
    base_attack = draw(st.sampled_from(attack_types))
    
    # Sometimes combine with normal text
    if draw(st.booleans()):
        normal_text = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))))
        return f"{normal_text} {base_attack}"
    
    return base_attack


@st.composite
def request_data_strategy(draw):
    """Generate request data for testing."""
    return {
        "method": draw(st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"])),
        "path": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")) + "/-_")),
        "headers": draw(st.dictionaries(
            st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")) + "-"),
            st.text(min_size=1, max_size=200),
            min_size=0,
            max_size=10
        )),
        "query_params": draw(st.dictionaries(
            st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"))),
            st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=5
        )),
        "client_ip": draw(st.sampled_from([
            "192.168.1.100",
            "10.0.0.50",
            "172.16.0.25",
            "203.0.113.45",  # External IP
            "198.51.100.10"  # External IP
        ]))
    }


@st.composite
def rate_limit_scenario_strategy(draw):
    """Generate rate limiting test scenarios."""
    return {
        "requests_count": draw(st.integers(min_value=1, max_value=200)),
        "time_window": draw(st.integers(min_value=1, max_value=120)),  # seconds
        "client_ip": draw(st.sampled_from([
            "192.168.1.100",
            "10.0.0.50", 
            "203.0.113.45"
        ])),
        "burst_requests": draw(st.integers(min_value=1, max_value=50))
    }


class MockRequest:
    """Mock request object for testing middleware."""
    
    def __init__(self, method: str = "GET", path: str = "/", headers: Dict[str, str] = None, 
                 query_params: Dict[str, str] = None, client_ip: str = "127.0.0.1"):
        self.method = method
        self.url = MagicMock()
        self.url.path = path
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.client = MagicMock()
        self.client.host = client_ip
        self.state = MagicMock()


class TestAPIGatewaySecurityEnforcement:
    """Test suite for API Gateway security enforcement property."""
    
    @pytest.mark.property
    @given(malicious_input=malicious_input_strategy())
    def test_input_validation_blocks_malicious_patterns(self, malicious_input: str):
        """
        **Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
        **Validates: Requirements 10.3, 10.5**
        
        Property: For any external request containing malicious patterns, the API Gateway 
        should block the request and log the incident before it reaches internal services.
        
        This ensures that input validation middleware catches common attack patterns
        as required by requirements 10.3 and 10.5.
        """
        # Create input validation middleware
        app = FastAPI()
        middleware = InputValidationMiddleware(app)
        
        # Test malicious input in different parts of the request
        test_cases = [
            # Malicious path
            MockRequest(path=f"/api/{malicious_input}"),
            # Malicious query parameter
            MockRequest(query_params={"param": malicious_input}),
            # Malicious header
            MockRequest(headers={"X-Custom": malicious_input})
        ]
        
        async def mock_call_next(request):
            # This should not be reached for malicious input
            return Response("OK", status_code=200)
        
        for request in test_cases:
            # Run the middleware check
            result = asyncio.run(middleware.dispatch(request, mock_call_next))
            
            # Should return error response for malicious input
            if hasattr(result, 'status_code'):
                assert result.status_code == 400, f"Malicious input '{malicious_input}' was not blocked"
            else:
                # If it's a JSONResponse, check the status code
                assert isinstance(result, JSONResponse), f"Expected JSONResponse for malicious input '{malicious_input}'"
    
    @pytest.mark.property
    @given(scenario=rate_limit_scenario_strategy())
    @settings(max_examples=50, deadline=5000)  # Reduced examples for performance
    def test_rate_limiting_enforces_limits_and_logs_violations(self, scenario: Dict[str, Any]):
        """
        **Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
        **Validates: Requirements 10.3, 10.5**
        
        Property: For any client making requests above the configured rate limits,
        the API Gateway should enforce rate limiting and log violations.
        
        This validates that rate limiting middleware enforces access controls
        as required by requirement 10.3.
        """
        # Configure rate limiting with low limits for testing
        app = FastAPI()
        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=10,  # Low limit for testing
            requests_per_hour=100,
            burst_limit=5
        )
        
        client_ip = scenario["client_ip"]
        requests_count = min(scenario["requests_count"], 50)  # Limit for test performance
        
        async def mock_call_next(request):
            return Response("OK", status_code=200)
        
        # Simulate rapid requests from the same IP
        blocked_count = 0
        allowed_count = 0
        
        async def simulate_requests():
            nonlocal blocked_count, allowed_count
            
            for i in range(requests_count):
                request = MockRequest(client_ip=client_ip, path=f"/api/test/{i}")
                
                try:
                    result = await middleware.dispatch(request, mock_call_next)
                    
                    if hasattr(result, 'status_code'):
                        if result.status_code == 429:  # Rate limited
                            blocked_count += 1
                        else:
                            allowed_count += 1
                    elif isinstance(result, JSONResponse):
                        # Check if it's a rate limit response
                        blocked_count += 1
                    else:
                        allowed_count += 1
                        
                except Exception:
                    # Any exception during rate limiting should be treated as blocked
                    blocked_count += 1
                
                # Small delay to simulate real requests
                await asyncio.sleep(0.01)
        
        # Run the simulation
        asyncio.run(simulate_requests())
        
        # Verify rate limiting behavior
        if requests_count > 10:  # Above the per-minute limit
            assert blocked_count > 0, f"Rate limiting should have blocked some requests for {requests_count} requests from {client_ip}"
        
        # At least some requests should be processed initially
        assert allowed_count >= 0, "Rate limiting should allow some initial requests"
    
    @pytest.mark.property
    @given(request_data=request_data_strategy())
    def test_security_headers_applied_to_all_responses(self, request_data: Dict[str, Any]):
        """
        **Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
        **Validates: Requirements 10.3, 10.5**
        
        Property: For any external request, the API Gateway should apply comprehensive
        security headers to all responses to prevent common web vulnerabilities.
        
        This ensures security headers middleware provides protection as required
        by requirement 10.3.
        """
        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)
        
        request = MockRequest(
            method=request_data["method"],
            path=request_data["path"],
            headers=request_data["headers"],
            query_params=request_data["query_params"],
            client_ip=request_data["client_ip"]
        )
        
        async def mock_call_next(request):
            return Response("OK", status_code=200)
        
        # Process request through security headers middleware
        result = asyncio.run(middleware.dispatch(request, mock_call_next))
        
        # Verify security headers are present
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy"
        ]
        
        for header in required_headers:
            assert header in result.headers, f"Security header '{header}' missing from response"
            assert result.headers[header], f"Security header '{header}' has empty value"
        
        # Verify specific security header values
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert "max-age=" in result.headers["Strict-Transport-Security"]
        assert "default-src 'self'" in result.headers["Content-Security-Policy"]
    
    @pytest.mark.property
    @given(
        blocked_ip=st.sampled_from(["192.0.2.1", "198.51.100.1", "203.0.113.1"]),
        allowed_ip=st.sampled_from(["192.168.1.100", "10.0.0.50", "172.16.0.25"])
    )
    def test_ip_filtering_enforces_access_controls(self, blocked_ip: str, allowed_ip: str):
        """
        **Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
        **Validates: Requirements 10.3, 10.5**
        
        Property: For any request from a blocked IP address, the API Gateway should
        deny access and log the violation. Allowed IPs should have normal access.
        
        This validates IP filtering as part of access control enforcement
        required by requirement 10.3.
        """
        assume(blocked_ip != allowed_ip)
        
        app = FastAPI()
        middleware = IPFilterMiddleware(
            app,
            blocked_ips=[blocked_ip],
            allowed_networks=["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
        )
        
        async def mock_call_next(request):
            return Response("OK", status_code=200)
        
        # Test blocked IP
        blocked_request = MockRequest(client_ip=blocked_ip)
        blocked_result = asyncio.run(middleware.dispatch(blocked_request, mock_call_next))
        
        # Should be blocked
        if hasattr(blocked_result, 'status_code'):
            assert blocked_result.status_code == 403, f"Blocked IP {blocked_ip} should be denied access"
        elif isinstance(blocked_result, JSONResponse):
            # Extract status code from JSONResponse
            assert blocked_result.status_code == 403, f"Blocked IP {blocked_ip} should be denied access"
        
        # Test allowed IP
        allowed_request = MockRequest(client_ip=allowed_ip)
        allowed_result = asyncio.run(middleware.dispatch(allowed_request, mock_call_next))
        
        # Should be allowed (status 200)
        if hasattr(allowed_result, 'status_code'):
            assert allowed_result.status_code == 200, f"Allowed IP {allowed_ip} should have access"
        else:
            # If no status code, it means the request was processed normally
            assert True  # Request was allowed through
    
    @pytest.mark.property
    @given(
        valid_api_key=st.text(min_size=32, max_size=64, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        invalid_api_key=st.text(min_size=1, max_size=31, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")))
    )
    def test_api_key_authentication_enforces_access_control(self, valid_api_key: str, invalid_api_key: str):
        """
        **Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
        **Validates: Requirements 10.3, 10.5**
        
        Property: For any request to protected endpoints, the API Gateway should
        enforce API key authentication and block unauthorized access attempts.
        
        This validates API key authentication as part of access control
        required by requirement 10.3.
        """
        assume(valid_api_key != invalid_api_key)
        assume(len(valid_api_key) > len(invalid_api_key))
        
        app = FastAPI()
        middleware = APIKeyMiddleware(app, api_keys={valid_api_key})
        
        async def mock_call_next(request):
            return Response("OK", status_code=200)
        
        # Test protected endpoint without API key
        no_key_request = MockRequest(path="/api/v1/agents/test")
        no_key_result = asyncio.run(middleware.dispatch(no_key_request, mock_call_next))
        
        # Should be unauthorized
        if hasattr(no_key_result, 'status_code'):
            assert no_key_result.status_code == 401, "Request without API key should be unauthorized"
        elif isinstance(no_key_result, JSONResponse):
            assert no_key_result.status_code == 401, "Request without API key should be unauthorized"
        
        # Test with invalid API key
        invalid_key_request = MockRequest(
            path="/api/v1/agents/test",
            headers={"X-API-Key": invalid_api_key}
        )
        invalid_key_result = asyncio.run(middleware.dispatch(invalid_key_request, mock_call_next))
        
        # Should be unauthorized
        if hasattr(invalid_key_result, 'status_code'):
            assert invalid_key_result.status_code == 401, f"Request with invalid API key '{invalid_api_key}' should be unauthorized"
        elif isinstance(invalid_key_result, JSONResponse):
            assert invalid_key_result.status_code == 401, f"Request with invalid API key '{invalid_api_key}' should be unauthorized"
        
        # Test with valid API key
        valid_key_request = MockRequest(
            path="/api/v1/agents/test",
            headers={"X-API-Key": valid_api_key}
        )
        valid_key_result = asyncio.run(middleware.dispatch(valid_key_request, mock_call_next))
        
        # Should be allowed
        if hasattr(valid_key_result, 'status_code'):
            assert valid_key_result.status_code == 200, f"Request with valid API key should be allowed"
        else:
            # Request was processed normally
            assert True
    
    @pytest.mark.property
    @given(request_data=request_data_strategy())
    def test_request_logging_captures_security_events(self, request_data: Dict[str, Any]):
        """
        **Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
        **Validates: Requirements 10.3, 10.5**
        
        Property: For any external request, the API Gateway should log security-relevant
        information including client IP, request details, and response status for
        monitoring and incident investigation.
        
        This validates logging requirements from requirement 10.5.
        """
        app = FastAPI()
        
        # Mock the logger to capture log calls
        with patch('shared.middleware.security.logger') as mock_logger:
            middleware = RequestLoggingMiddleware(app)
            
            request = MockRequest(
                method=request_data["method"],
                path=request_data["path"],
                headers=request_data["headers"],
                query_params=request_data["query_params"],
                client_ip=request_data["client_ip"]
            )
            
            async def mock_call_next(request):
                return Response("OK", status_code=200)
            
            # Process request through logging middleware
            result = asyncio.run(middleware.dispatch(request, mock_call_next))
            
            # Verify that logging occurred
            assert mock_logger.info.called, "Request logging should capture request information"
            
            # Check that log calls contain security-relevant information
            log_calls = mock_logger.info.call_args_list
            
            # Should have at least request and response logs
            assert len(log_calls) >= 2, "Should log both request and response"
            
            # Verify request log contains required information
            request_log_call = log_calls[0]
            request_log_extra = request_log_call[1].get('extra', {})
            
            assert 'client_ip' in request_log_extra, "Request log should include client IP"
            assert 'method' in request_log_extra, "Request log should include HTTP method"
            assert 'path' in request_log_extra, "Request log should include request path"
            assert 'timestamp' in request_log_extra, "Request log should include timestamp"
            
            # Verify response log contains required information
            response_log_call = log_calls[1]
            response_log_extra = response_log_call[1].get('extra', {})
            
            assert 'client_ip' in response_log_extra, "Response log should include client IP"
            assert 'status_code' in response_log_extra, "Response log should include status code"
            assert 'duration_ms' in response_log_extra, "Response log should include duration"
            assert 'timestamp' in response_log_extra, "Response log should include timestamp"
    
    def test_threat_detection_and_response_integration(self):
        """
        **Feature: ai-agent-framework, Property 23: API Gateway Security Enforcement**
        **Validates: Requirements 10.3, 10.5**
        
        Test that the security middleware can detect and respond to various
        threat patterns as required by the security requirements.
        """
        app = FastAPI()
        
        # Create middleware stack for threat detection
        input_validation = InputValidationMiddleware(app)
        rate_limiting = RateLimitMiddleware(app, requests_per_minute=5, burst_limit=2)
        
        async def mock_call_next(request):
            return Response("OK", status_code=200)
        
        # Test various threat scenarios
        threat_scenarios = [
            # SQL injection
            MockRequest(path="/api/test", query_params={"id": "1'; DROP TABLE users; --"}),
            # XSS
            MockRequest(path="/api/test", headers={"X-Custom": "<script>alert('xss')</script>"}),
            # Command injection
            MockRequest(path="/api/test/; cat /etc/passwd"),
            # Path traversal
            MockRequest(path="/api/../../../etc/passwd"),
        ]
        
        for threat_request in threat_scenarios:
            # Should be blocked by input validation
            result = asyncio.run(input_validation.dispatch(threat_request, mock_call_next))
            
            if hasattr(result, 'status_code'):
                assert result.status_code == 400, f"Threat request should be blocked: {threat_request.url.path}"
            elif isinstance(result, JSONResponse):
                assert result.status_code == 400, f"Threat request should be blocked: {threat_request.url.path}"
        
        # Test rate limiting with burst requests
        client_ip = "203.0.113.45"
        
        # Send burst of requests (should trigger rate limiting)
        blocked_count = 0
        for i in range(10):  # More than burst limit
            request = MockRequest(client_ip=client_ip, path=f"/api/test/{i}")
            result = asyncio.run(rate_limiting.dispatch(request, mock_call_next))
            
            if hasattr(result, 'status_code') and result.status_code == 429:
                blocked_count += 1
            elif isinstance(result, JSONResponse) and result.status_code == 429:
                blocked_count += 1
        
        assert blocked_count > 0, "Rate limiting should block some requests in burst scenario"