# Guardrails Engine Implementation
from typing import Dict, Any, Optional, List, Set, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import re
import asyncio
import uuid
from dataclasses import dataclass
import hashlib
import time

from ..models.tenant import Tenant
from ..models.audit import AuditLog, AuditEventType, AuditOutcome, AuditSeverity
from .base import BaseService

logger = logging.getLogger(__name__)


class ViolationType(str, Enum):
    """Types of guardrail violations"""
    HARMFUL_CONTENT = "harmful_content"
    INAPPROPRIATE_LANGUAGE = "inappropriate_language"
    PII_EXPOSURE = "pii_exposure"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_THREAT = "security_threat"
    PROMPT_INJECTION = "prompt_injection"
    DATA_LEAKAGE = "data_leakage"
    TOXIC_CONTENT = "toxic_content"
    BIAS_DETECTION = "bias_detection"


class RiskLevel(str, Enum):
    """Risk levels for content assessment"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentCategory(str, Enum):
    """Categories of content for filtering"""
    GENERAL = "general"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    LEGAL = "legal"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    TECHNICAL = "technical"


@dataclass
class ValidationContext:
    """Context for validation operations"""
    tenant_id: str
    user_id: Optional[str]
    agent_id: Optional[str]
    session_id: Optional[str]
    content_category: ContentCategory
    source: str  # 'input' or 'output'
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class ValidationResult:
    """Result of content validation"""
    is_valid: bool
    violations: List[str]
    violation_types: List[ViolationType]
    risk_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    sanitized_content: Optional[str]
    blocked_phrases: List[str]
    confidence: float  # 0.0 to 1.0
    processing_time_ms: float
    metadata: Dict[str, Any]


@dataclass
class PolicyResult:
    """Result of policy check"""
    allowed: bool
    policy_name: str
    reason: str
    risk_score: float
    metadata: Dict[str, Any]


@dataclass
class Violation:
    """Guardrail violation record"""
    id: str
    tenant_id: str
    user_id: Optional[str]
    agent_id: Optional[str]
    violation_type: ViolationType
    risk_level: RiskLevel
    content_hash: str
    original_content: str
    sanitized_content: Optional[str]
    context: ValidationContext
    timestamp: datetime
    resolved: bool
    resolution_notes: Optional[str]


class ContentFilter:
    """Content filtering with pattern matching and ML-based detection"""
    
    def __init__(self):
        self.harmful_patterns = self._load_harmful_patterns()
        self.pii_patterns = self._load_pii_patterns()
        self.prompt_injection_patterns = self._load_prompt_injection_patterns()
        self.toxic_keywords = self._load_toxic_keywords()
    
    def _load_harmful_patterns(self) -> List[re.Pattern]:
        """Load harmful content patterns"""
        patterns = [
            # Violence and threats
            r'\b(kill|murder|assassinate|bomb|terrorist|violence)\b',
            r'\b(suicide|self-harm|hurt yourself)\b',
            r'\b(weapon|gun|knife|explosive)\b',
            
            # Hate speech
            r'\b(hate|racist|nazi|supremacist)\b',
            r'\b(discriminat|prejudice|bigot)\b',
            
            # Illegal activities
            r'\b(drug dealing|money laundering|fraud|scam)\b',
            r'\b(hack|crack|exploit|malware)\b',
            
            # Adult content
            r'\b(explicit|pornographic|sexual|adult content)\b',
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _load_pii_patterns(self) -> List[re.Pattern]:
        """Load PII detection patterns"""
        patterns = [
            # Social Security Numbers
            r'\b\d{3}-\d{2}-\d{4}\b',
            r'\b\d{9}\b',
            
            # Credit Card Numbers
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            
            # Email addresses
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            
            # Phone numbers
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\(\d{3}\)\s?\d{3}[-.]?\d{4}',
            
            # IP addresses
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _load_prompt_injection_patterns(self) -> List[re.Pattern]:
        """Load prompt injection detection patterns"""
        patterns = [
            # Direct instruction attempts
            r'\b(ignore|forget|disregard)\s+(previous|above|all)\s+(instructions?|prompts?|rules?)\b',
            r'\b(act as|pretend to be|roleplay as)\b',
            r'\b(system prompt|system message|initial prompt)\b',
            
            # Jailbreak attempts
            r'\b(jailbreak|bypass|override)\b',
            r'\b(developer mode|admin mode|god mode)\b',
            r'\b(unrestricted|unlimited|no limits)\b',
            
            # Prompt leakage attempts
            r'\b(show me your|what is your|reveal your)\s+(prompt|instructions|system message)\b',
            r'\b(copy|repeat|echo)\s+(your|the)\s+(prompt|instructions)\b',
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _load_toxic_keywords(self) -> Set[str]:
        """Load toxic keywords list"""
        # This would typically be loaded from a comprehensive database
        return {
            'hate', 'toxic', 'offensive', 'abusive', 'harassment',
            'discrimination', 'bullying', 'threatening', 'violent'
        }
    
    async def detect_harmful_content(self, content: str) -> List[str]:
        """Detect harmful content patterns"""
        violations = []
        
        for pattern in self.harmful_patterns:
            matches = pattern.findall(content)
            if matches:
                violations.extend([f"Harmful content detected: {match}" for match in matches])
        
        return violations
    
    async def detect_pii(self, content: str) -> List[str]:
        """Detect personally identifiable information"""
        violations = []
        
        for pattern in self.pii_patterns:
            matches = pattern.findall(content)
            if matches:
                violations.extend([f"PII detected: {match}" for match in matches])
        
        return violations
    
    async def detect_prompt_injection(self, content: str) -> List[str]:
        """Detect prompt injection attempts"""
        violations = []
        
        for pattern in self.prompt_injection_patterns:
            matches = pattern.findall(content)
            if matches:
                violations.extend([f"Prompt injection detected: {match}" for match in matches])
        
        return violations
    
    async def detect_toxic_content(self, content: str) -> List[str]:
        """Detect toxic content using keyword matching"""
        violations = []
        content_lower = content.lower()
        
        for keyword in self.toxic_keywords:
            if keyword in content_lower:
                violations.append(f"Toxic content detected: {keyword}")
        
        return violations
    
    def sanitize_content(self, content: str, violations: List[str]) -> str:
        """Sanitize content by removing or masking violations"""
        sanitized = content
        
        # Mask PII
        for pattern in self.pii_patterns:
            sanitized = pattern.sub('[REDACTED]', sanitized)
        
        # Remove harmful patterns
        for pattern in self.harmful_patterns:
            sanitized = pattern.sub('[FILTERED]', sanitized)
        
        return sanitized


class MLContentAnalyzer:
    """ML-based content analysis (placeholder for future ML integration)"""
    
    def __init__(self):
        self.model_loaded = False
        # In a real implementation, this would load ML models
        # For now, we'll use rule-based scoring
    
    async def analyze_sentiment(self, content: str) -> Dict[str, float]:
        """Analyze content sentiment"""
        # Placeholder implementation
        # In production, this would use a trained sentiment analysis model
        
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'angry', 'sad']
        positive_words = ['good', 'great', 'excellent', 'love', 'happy', 'amazing']
        
        content_lower = content.lower()
        negative_score = sum(1 for word in negative_words if word in content_lower)
        positive_score = sum(1 for word in positive_words if word in content_lower)
        
        total_words = len(content.split())
        if total_words == 0:
            return {'positive': 0.5, 'negative': 0.5, 'neutral': 0.0}
        
        negative_ratio = negative_score / total_words
        positive_ratio = positive_score / total_words
        neutral_ratio = max(0, 1 - negative_ratio - positive_ratio)
        
        return {
            'positive': min(1.0, positive_ratio * 10),
            'negative': min(1.0, negative_ratio * 10),
            'neutral': neutral_ratio
        }
    
    async def calculate_toxicity_score(self, content: str) -> float:
        """Calculate toxicity score (0.0 to 1.0)"""
        # Placeholder implementation
        # In production, this would use a trained toxicity detection model
        
        toxic_indicators = [
            'hate', 'kill', 'die', 'stupid', 'idiot', 'moron',
            'shut up', 'go away', 'nobody cares', 'worthless'
        ]
        
        content_lower = content.lower()
        toxic_count = sum(1 for indicator in toxic_indicators if indicator in content_lower)
        
        # Simple scoring based on toxic word density
        words = content.split()
        if len(words) == 0:
            return 0.0
        
        toxicity_score = min(1.0, (toxic_count / len(words)) * 10)
        return toxicity_score
    
    async def detect_bias(self, content: str) -> Dict[str, float]:
        """Detect potential bias in content"""
        # Placeholder implementation
        # In production, this would use trained bias detection models
        
        bias_categories = {
            'gender': 0.0,
            'racial': 0.0,
            'religious': 0.0,
            'age': 0.0,
            'political': 0.0
        }
        
        # Simple keyword-based bias detection
        gender_bias_words = ['men are', 'women are', 'boys are', 'girls are']
        racial_bias_words = ['all blacks', 'all whites', 'all asians']
        religious_bias_words = ['all muslims', 'all christians', 'all jews']
        
        content_lower = content.lower()
        
        if any(word in content_lower for word in gender_bias_words):
            bias_categories['gender'] = 0.7
        
        if any(word in content_lower for word in racial_bias_words):
            bias_categories['racial'] = 0.8
        
        if any(word in content_lower for word in religious_bias_words):
            bias_categories['religious'] = 0.8
        
        return bias_categories


class GuardrailsEngine:
    """Main guardrails engine for content validation and policy enforcement"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.content_filter = ContentFilter()
        self.ml_analyzer = MLContentAnalyzer()
        self.violations_cache = {}
        self.policy_cache = {}
    
    async def validate_input(
        self,
        content: str,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate input content against guardrails"""
        start_time = time.time()
        
        try:
            # Run all validation checks concurrently
            tasks = [
                self.content_filter.detect_harmful_content(content),
                self.content_filter.detect_pii(content),
                self.content_filter.detect_prompt_injection(content),
                self.content_filter.detect_toxic_content(content),
                self.ml_analyzer.analyze_sentiment(content),
                self.ml_analyzer.calculate_toxicity_score(content),
                self.ml_analyzer.detect_bias(content)
            ]
            
            results = await asyncio.gather(*tasks)
            
            harmful_violations = results[0]
            pii_violations = results[1]
            injection_violations = results[2]
            toxic_violations = results[3]
            sentiment = results[4]
            toxicity_score = results[5]
            bias_scores = results[6]
            
            # Combine all violations
            all_violations = (
                harmful_violations + pii_violations + 
                injection_violations + toxic_violations
            )
            
            # Determine violation types
            violation_types = []
            if harmful_violations:
                violation_types.append(ViolationType.HARMFUL_CONTENT)
            if pii_violations:
                violation_types.append(ViolationType.PII_EXPOSURE)
            if injection_violations:
                violation_types.append(ViolationType.PROMPT_INJECTION)
            if toxic_violations:
                violation_types.append(ViolationType.TOXIC_CONTENT)
            if max(bias_scores.values()) > 0.5:
                violation_types.append(ViolationType.BIAS_DETECTION)
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(
                len(all_violations),
                toxicity_score,
                sentiment,
                bias_scores
            )
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Determine if content is valid
            is_valid = risk_score < 0.7 and len(all_violations) == 0
            
            # Sanitize content if needed
            sanitized_content = None
            if not is_valid:
                sanitized_content = self.content_filter.sanitize_content(content, all_violations)
            
            processing_time = (time.time() - start_time) * 1000
            
            result = ValidationResult(
                is_valid=is_valid,
                violations=all_violations,
                violation_types=violation_types,
                risk_score=risk_score,
                risk_level=risk_level,
                sanitized_content=sanitized_content,
                blocked_phrases=[v.split(': ')[1] for v in all_violations if ': ' in v],
                confidence=0.85,  # Placeholder confidence score
                processing_time_ms=processing_time,
                metadata={
                    'sentiment': sentiment,
                    'toxicity_score': toxicity_score,
                    'bias_scores': bias_scores,
                    'content_length': len(content),
                    'word_count': len(content.split())
                }
            )
            
            # Log violation if content is invalid
            if not is_valid:
                await self._log_violation(content, result, context)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in input validation: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return ValidationResult(
                is_valid=False,
                violations=[f"Validation error: {str(e)}"],
                violation_types=[ViolationType.SECURITY_THREAT],
                risk_score=1.0,
                risk_level=RiskLevel.CRITICAL,
                sanitized_content=None,
                blocked_phrases=[],
                confidence=0.0,
                processing_time_ms=processing_time,
                metadata={'error': str(e)}
            )
    
    async def validate_output(
        self,
        content: str,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate output content against guardrails"""
        # Output validation uses similar logic but with different thresholds
        context.source = 'output'
        result = await self.validate_input(content, context)
        
        # Output validation is typically more lenient
        if result.risk_score < 0.8:
            result.is_valid = True
        
        return result
    
    async def check_policy(
        self,
        action: str,
        resource: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> PolicyResult:
        """Check if action is allowed by policies"""
        try:
            # Get tenant policies
            tenant_policies = await self._get_tenant_policies()
            
            # Check each applicable policy
            for policy in tenant_policies:
                if self._policy_applies(policy, action, resource, context):
                    if not policy.get('allowed', True):
                        return PolicyResult(
                            allowed=False,
                            policy_name=policy['name'],
                            reason=policy.get('reason', 'Action not allowed by policy'),
                            risk_score=policy.get('risk_score', 0.5),
                            metadata=policy.get('metadata', {})
                        )
            
            # Default allow if no blocking policies
            return PolicyResult(
                allowed=True,
                policy_name='default',
                reason='No blocking policies found',
                risk_score=0.1,
                metadata={}
            )
            
        except Exception as e:
            logger.error(f"Error in policy check: {e}")
            return PolicyResult(
                allowed=False,
                policy_name='error',
                reason=f"Policy check error: {str(e)}",
                risk_score=1.0,
                metadata={'error': str(e)}
            )
    
    async def report_violation(self, violation: Violation) -> None:
        """Report and log a guardrail violation"""
        try:
            # Create audit log entry
            audit_entry = AuditLog(
                event_type=AuditEventType.GUARDRAIL_TRIGGERED,
                event_id=str(uuid.uuid4()),
                correlation_id=violation.id, # Use violation id as correlation if not available
                tenant_id=violation.tenant_id,
                user_id=violation.user_id,
                action="guardrail_violation",
                resource_type="content",
                resource_id=violation.id,
                details={
                    'violation_type': violation.violation_type.value,
                    'risk_level': violation.risk_level.value,
                    'content_hash': violation.content_hash,
                    'agent_id': violation.agent_id,
                    'context': violation.context.__dict__
                },
                outcome=AuditOutcome.FAILURE,
                severity=AuditSeverity.HIGH if violation.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else AuditSeverity.MEDIUM,
                timestamp=violation.timestamp
            )
            
            self.session.add(audit_entry)
            await self.session.commit()
            
            # Send notification if risk level is high or critical
            if violation.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await self._send_violation_notification(violation)
            
            logger.warning(
                f"Guardrail violation reported: {violation.violation_type.value} "
                f"(Risk: {violation.risk_level.value}) for tenant {violation.tenant_id}"
            )
            
        except Exception as e:
            logger.error(f"Error reporting violation: {e}")
    
    def _calculate_risk_score(
        self,
        violation_count: int,
        toxicity_score: float,
        sentiment: Dict[str, float],
        bias_scores: Dict[str, float]
    ) -> float:
        """Calculate overall risk score"""
        # Base score from violations
        base_score = min(1.0, violation_count * 0.2)
        
        # Add toxicity score
        toxicity_weight = 0.3
        toxicity_contribution = toxicity_score * toxicity_weight
        
        # Add negative sentiment contribution
        sentiment_weight = 0.2
        sentiment_contribution = sentiment.get('negative', 0) * sentiment_weight
        
        # Add bias contribution
        bias_weight = 0.3
        max_bias = max(bias_scores.values()) if bias_scores else 0
        bias_contribution = max_bias * bias_weight
        
        # Combine scores
        total_score = base_score + toxicity_contribution + sentiment_contribution + bias_contribution
        
        return min(1.0, total_score)
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score"""
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def _log_violation(
        self,
        content: str,
        result: ValidationResult,
        context: ValidationContext
    ) -> None:
        """Log a guardrail violation"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        violation = Violation(
            id=f"violation_{int(time.time())}_{content_hash[:8]}",
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            agent_id=context.agent_id,
            violation_type=result.violation_types[0] if result.violation_types else ViolationType.POLICY_VIOLATION,
            risk_level=result.risk_level,
            content_hash=content_hash,
            original_content=content[:1000],  # Limit stored content length
            sanitized_content=result.sanitized_content,
            context=context,
            timestamp=datetime.utcnow(),
            resolved=False,
            resolution_notes=None
        )
        
        await self.report_violation(violation)
    
    async def _get_tenant_policies(self) -> List[Dict[str, Any]]:
        """Get tenant-specific policies"""
        # This would typically load from database
        # For now, return default policies
        return [
            {
                'name': 'no_harmful_content',
                'action': '*',
                'resource': '*',
                'allowed': True,
                'conditions': {
                    'max_risk_score': 0.7
                }
            },
            {
                'name': 'no_pii_exposure',
                'action': 'generate_response',
                'resource': 'agent_output',
                'allowed': True,
                'conditions': {
                    'no_pii': True
                }
            }
        ]
    
    def _policy_applies(
        self,
        policy: Dict[str, Any],
        action: str,
        resource: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if policy applies to the given action and resource"""
        # Check action match
        if policy.get('action') != '*' and policy.get('action') != action:
            return False
        
        # Check resource match
        if policy.get('resource') != '*' and policy.get('resource') != resource:
            return False
        
        # Check conditions
        conditions = policy.get('conditions', {})
        for condition_key, condition_value in conditions.items():
            if condition_key not in context:
                continue
            
            if context[condition_key] != condition_value:
                return False
        
        return True
    
    async def _send_violation_notification(self, violation: Violation) -> None:
        """Send notification for high-risk violations"""
        # This would integrate with notification system
        # For now, just log
        logger.critical(
            f"HIGH RISK VIOLATION: {violation.violation_type.value} "
            f"in tenant {violation.tenant_id} by user {violation.user_id}"
        )


class GuardrailsService(BaseService):
    """Service wrapper for guardrails engine"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)
        self.engines = {}  # Cache engines per tenant
    
    def get_engine(self, tenant_id: str) -> GuardrailsEngine:
        """Get or create guardrails engine for tenant"""
        if tenant_id not in self.engines:
            self.engines[tenant_id] = GuardrailsEngine(self.session, tenant_id)
        return self.engines[tenant_id]
    
    async def validate_agent_input(
        self,
        tenant_id: str,
        agent_id: str,
        user_id: str,
        content: str,
        session_id: Optional[str] = None
    ) -> ValidationResult:
        """Validate agent input content"""
        engine = self.get_engine(tenant_id)
        
        context = ValidationContext(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            content_category=ContentCategory.GENERAL,
            source='input',
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        return await engine.validate_input(content, context)
    
    async def validate_agent_output(
        self,
        tenant_id: str,
        agent_id: str,
        user_id: str,
        content: str,
        session_id: Optional[str] = None
    ) -> ValidationResult:
        """Validate agent output content"""
        engine = self.get_engine(tenant_id)
        
        context = ValidationContext(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            content_category=ContentCategory.GENERAL,
            source='output',
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        return await engine.validate_output(content, context)
    
    async def check_agent_policy(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        """Check if action is allowed by tenant policies"""
        engine = self.get_engine(tenant_id)
        return await engine.check_policy(action, resource, user_id, context or {})
    
    async def get_violation_stats(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get violation statistics for tenant"""
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Query audit logs for violations
        stmt = select(
            func.count(AuditLog.id).label('total_violations'),
            func.count(AuditLog.id).filter(
                AuditLog.details['risk_level'].astext == 'critical'
            ).label('critical_violations'),
            func.count(AuditLog.id).filter(
                AuditLog.details['risk_level'].astext == 'high'
            ).label('high_violations')
        ).where(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action == 'guardrail_violation',
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )
        )
        
        result = await self.session.execute(stmt)
        stats = result.first()
        
        return {
            'tenant_id': tenant_id,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'total_violations': stats.total_violations or 0,
            'critical_violations': stats.critical_violations or 0,
            'high_violations': stats.high_violations or 0,
            'medium_violations': (stats.total_violations or 0) - (stats.critical_violations or 0) - (stats.high_violations or 0)
        }