"""
Pagination utilities for API responses.

This module provides:
- Pagination parameter parsing
- Paginated result formatting
- Pagination metadata generation
"""

from typing import TypeVar, Generic, List, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters for API requests."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", regex="^(asc|desc)$", description="Sort order")


class PaginatedResult(BaseModel, Generic[T]):
    """Paginated result wrapper."""
    
    items: List[T]
    total: int
    page: int
    per_page: int
    
    @property
    def pages(self) -> int:
        """Total number of pages."""
        return (self.total + self.per_page - 1) // self.per_page
    
    @property
    def has_next(self) -> bool:
        """Whether there is a next page."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Whether there is a previous page."""
        return self.page > 1
    
    @property
    def next_page(self) -> Optional[int]:
        """Next page number."""
        return self.page + 1 if self.has_next else None
    
    @property
    def prev_page(self) -> Optional[int]:
        """Previous page number."""
        return self.page - 1 if self.has_prev else None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "items": [item.dict() if hasattr(item, 'dict') else item for item in self.items],
            "pagination": {
                "page": self.page,
                "per_page": self.per_page,
                "total": self.total,
                "pages": self.pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev,
                "next_page": self.next_page,
                "prev_page": self.prev_page
            }
        }