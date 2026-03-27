"""API routers (organized by domain)"""

from .mesh import router as mesh_router
from .research import router as research_router
from .health import router as health_router
from .projects import router as projects_router
from .newsletter import router as newsletter_router
from .deployment import router as deployment_router
from .images import router as images_router
from .status import router as status_router
from .reels import router as reels_router
from .psychology import router as psychology_router
from .me import router as me_router
from .settings import router as settings_router
from .creator_profile import router as creator_profile_router
from .personas import router as personas_router
from .idea_pool import router as idea_pool_router

__all__ = [
    "mesh_router",
    "research_router",
    "health_router",
    "projects_router",
    "newsletter_router",
    "deployment_router",
    "images_router",
    "status_router",
    "reels_router",
    "psychology_router",
    "me_router",
    "settings_router",
    "creator_profile_router",
    "personas_router",
    "idea_pool_router",
]
