"""Process-wide singletons shared by both transports (REST + MCP).

Sharing instances (not just classes) matters here: the circuit breakers and
the partner-config cache need to reflect one real view of downstream health,
not a duplicate per transport.
"""

from app.services.member_client import MockMemberDataClient
from app.services.partner_config_client import MockPartnerConfigClient
from app.services.recommendation_orchestrator import RecommendationOrchestrator

member_client = MockMemberDataClient()
partner_config_client = MockPartnerConfigClient()
orchestrator = RecommendationOrchestrator(member_client, partner_config_client)
