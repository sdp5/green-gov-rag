"""Admin panel for GreenGovRAG.

Provides administrative interface for:
- Document management
- Query analytics
- Vector store monitoring
- System configuration
"""

from green_gov_rag.api.admin.router import router

__all__ = ["router"]
