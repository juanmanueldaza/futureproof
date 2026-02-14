"""Service layer for FutureProof business logic.

SRP-compliant service architecture:
- GathererService: Data collection operations
- AnalysisService: Career analysis and advice
- KnowledgeService: RAG knowledge base indexing and search
"""

from .analysis_service import AnalysisAction, AnalysisResult, AnalysisService
from .exceptions import AnalysisError, NoDataError, ServiceError
from .gatherer_service import GathererService
from .knowledge_service import KnowledgeService

__all__ = [
    # Services
    "AnalysisService",
    "GathererService",
    "KnowledgeService",
    # Types
    "AnalysisAction",
    "AnalysisResult",
    # Exceptions
    "AnalysisError",
    "NoDataError",
    "ServiceError",
]
