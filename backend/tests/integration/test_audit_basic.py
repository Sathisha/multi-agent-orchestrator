"""Basic test to verify audit system implementation."""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all audit components can be imported."""
    print("🔧 Testing audit system imports...")
    
    # Test model imports
    from shared.models.audit import (
        AuditLog, AuditEventType, AuditSeverity, AuditOutcome,
        AuditLogRequest, AuditLogResponse, AuditStatistics, ComplianceReport
    )
    print("✅ Audit models imported successfully")
    
    # Test service imports
    from shared.services.audit import AuditService
    from shared.services.forensic_analysis import ForensicAnalysisService
    from shared.services.compliance_monitoring import ComplianceMonitoringService
    print("✅ Audit services imported successfully")
    
    # Test API imports
    from shared.api.audit import router
    print("✅ Audit API imported successfully")
    
    # Test middleware imports
    from shared.middleware.audit import AuditMiddleware
    print("✅ Audit middleware imported successfully")