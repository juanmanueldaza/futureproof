"""Service layer for FutureProof business logic.

SRP-compliant service architecture:
- CareerService: Unified facade (backward compatible)
- GathererService: Data collection operations
- AnalysisService: Career analysis and advice
- GenerationService: CV generation
- KnowledgeService: RAG knowledge base indexing and search
"""

from .analysis_service import AnalysisAction, AnalysisResult, AnalysisService
from .career_service import CareerService
from .exceptions import AnalysisError, GenerationError, NoDataError, ServiceError
from .gatherer_service import GathererService
from .generation_service import GenerationService
from .knowledge_service import KnowledgeService

__all__ = [
    # Facade (primary interface - backward compatible)
    "CareerService",
    # Sub-services (for direct use if needed)
    "AnalysisService",
    "GathererService",
    "GenerationService",
    "KnowledgeService",
    # Types
    "AnalysisAction",
    "AnalysisResult",
    # Exceptions
    "AnalysisError",
    "GenerationError",
    "NoDataError",
    "ServiceError",
]
