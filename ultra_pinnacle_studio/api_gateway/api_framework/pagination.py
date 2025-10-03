"""
Universal Pagination, Filtering, and Sorting for Ultra Pinnacle AI Studio

This module provides standardized query parameter handling for:
- Pagination (page-based and cursor-based)
- Filtering (field-based and advanced filters)
- Sorting (single and multi-field)
- Search functionality
"""

from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from pydantic import BaseModel, Field, field_validator
from fastapi import Query, HTTPException
from sqlalchemy import desc, asc, and_, or_, func
from sqlalchemy.orm import Query as SQLAlchemyQuery
from enum import Enum
import re
import logging

logger = logging.getLogger("ultra_pinnacle")


class PaginationParams(BaseModel):
    """Standard pagination parameters"""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(50, ge=1, le=1000, description="Items per page")
    max_per_page: int = Field(1000, description="Maximum items per page")

    @field_validator('per_page')
    @classmethod
    def validate_per_page(cls, v, info):
        # Get the model instance to access max_per_page
        if hasattr(cls, 'max_per_page') and v > cls.max_per_page:
            raise ValueError(f"per_page cannot exceed {cls.max_per_page}")
        return v


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters"""

    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: int = Field(50, ge=1, le=1000, description="Number of items to return")
    direction: str = Field("forward", pattern="^(forward|backward)$", description="Pagination direction")


class SortOrder(str, Enum):
    """Sort order enumeration"""

    ASC = "asc"
    DESC = "desc"


class SortField(BaseModel):
    """Individual sort field"""

    field: str = Field(..., description="Field to sort by")
    order: SortOrder = Field(SortOrder.ASC, description="Sort order")

    @field_validator('field')
    @classmethod
    def validate_field_name(cls, v):
        # Basic validation - can be extended with allowed fields list
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$', v):
            raise ValueError("Invalid field name format")
        return v


class SortingParams(BaseModel):
    """Sorting parameters"""

    sort: List[SortField] = Field(default_factory=list, description="Sort fields and orders")

    @classmethod
    def from_query_string(cls, sort_string: Optional[str] = None) -> "SortingParams":
        """Parse sort parameter from query string like 'field1:asc,field2:desc'"""
        if not sort_string:
            return cls()

        sort_fields = []
        for part in sort_string.split(','):
            part = part.strip()
            if ':' in part:
                field, order = part.split(':', 1)
                field = field.strip()
                order = order.strip().lower()
                if order not in [SortOrder.ASC, SortOrder.DESC]:
                    order = SortOrder.ASC
                sort_fields.append(SortField(field=field, order=SortOrder(order)))
            else:
                # Default to ascending if no order specified
                sort_fields.append(SortField(field=part.strip(), order=SortOrder.ASC))

        return cls(sort=sort_fields)


class FilterOperator(str, Enum):
    """Filter operator enumeration"""

    EQ = "eq"          # equals
    NE = "ne"          # not equals
    GT = "gt"          # greater than
    GE = "ge"          # greater than or equal
    LT = "lt"          # less than
    LE = "le"          # less than or equal
    IN = "in"          # in list
    NIN = "nin"        # not in list
    CONTAINS = "contains"    # string contains
    ICONTAINS = "icontains"  # case-insensitive contains
    STARTS_WITH = "startswith"  # starts with
    ENDS_WITH = "endswith"    # ends with
    IS_NULL = "isnull"        # is null
    IS_NOT_NULL = "isnotnull" # is not null
    BETWEEN = "between"       # between two values


class FilterCondition(BaseModel):
    """Individual filter condition"""

    field: str = Field(..., description="Field to filter by")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(..., description="Filter value")

    @field_validator('field')
    @classmethod
    def validate_field_name(cls, v):
        # Basic validation - can be extended with allowed fields list
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$', v):
            raise ValueError("Invalid field name format")
        return v


class FilteringParams(BaseModel):
    """Filtering parameters"""

    filters: List[FilterCondition] = Field(default_factory=list, description="Filter conditions")

    @classmethod
    def from_query_params(cls, query_params: Dict[str, Any]) -> "FilteringParams":
        """Parse filter parameters from query parameters"""
        filters = []

        # Look for filter parameters (e.g., filter[field][operator]=value)
        filter_pattern = re.compile(r'^filter\[([^]]+)\]\[([^]]+)\]$')

        for key, value in query_params.items():
            match = filter_pattern.match(key)
            if match:
                field, operator = match.groups()
                try:
                    filter_op = FilterOperator(operator)
                    filters.append(FilterCondition(
                        field=field,
                        operator=filter_op,
                        value=value
                    ))
                except ValueError:
                    logger.warning(f"Invalid filter operator: {operator}")
                    continue

        return cls(filters=filters)


class SearchParams(BaseModel):
    """Search parameters"""

    query: Optional[str] = Field(None, description="Search query string")
    fields: List[str] = Field(default_factory=list, description="Fields to search in")
    fuzzy: bool = Field(False, description="Enable fuzzy search")


class QueryParams(BaseModel):
    """Combined query parameters for pagination, filtering, sorting, and search"""

    pagination: PaginationParams = Field(default_factory=PaginationParams)
    sorting: SortingParams = Field(default_factory=SortingParams)
    filtering: FilteringParams = Field(default_factory=FilteringParams)
    search: SearchParams = Field(default_factory=SearchParams)

    @classmethod
    def from_request(
        cls,
        page: int = Query(1, ge=1),
        per_page: int = Query(50, ge=1, le=1000),
        sort: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        search_fields: Optional[str] = Query(None),
        fuzzy: bool = Query(False),
        **filters
    ) -> "QueryParams":
        """Create QueryParams from FastAPI query parameters"""
        pagination = PaginationParams(page=page, per_page=per_page)
        sorting = SortingParams.from_query_string(sort)
        filtering = FilteringParams.from_query_params(filters)
        search_params = SearchParams(
            query=search,
            fields=search_fields.split(',') if search_fields else [],
            fuzzy=fuzzy
        )

        return cls(
            pagination=pagination,
            sorting=sorting,
            filtering=filtering,
            search=search_params
        )


def apply_pagination(query: SQLAlchemyQuery, params: PaginationParams) -> Tuple[SQLAlchemyQuery, PaginationParams]:
    """Apply pagination to SQLAlchemy query"""
    total_items = query.count()
    params.total_items = total_items
    params.total_pages = (total_items + params.per_page - 1) // params.per_page

    # Ensure page doesn't exceed total pages
    if params.page > params.total_pages and params.total_pages > 0:
        params.page = params.total_pages

    offset = (params.page - 1) * params.per_page
    query = query.offset(offset).limit(params.per_page)

    return query, params


def apply_sorting(query: SQLAlchemyQuery, params: SortingParams, model_class: Any) -> SQLAlchemyQuery:
    """Apply sorting to SQLAlchemy query"""
    if not params.sort:
        return query

    order_by_clauses = []
    for sort_field in params.sort:
        field_parts = sort_field.field.split('.')
        field_attr = getattr(model_class, field_parts[0])

        # Handle nested fields (relationships)
        for part in field_parts[1:]:
            field_attr = getattr(field_attr, part)

        if sort_field.order == SortOrder.DESC:
            order_by_clauses.append(desc(field_attr))
        else:
            order_by_clauses.append(asc(field_attr))

    if order_by_clauses:
        query = query.order_by(*order_by_clauses)

    return query


def apply_filtering(query: SQLAlchemyQuery, params: FilteringParams, model_class: Any) -> SQLAlchemyQuery:
    """Apply filtering to SQLAlchemy query"""
    if not params.filters:
        return query

    filter_conditions = []

    for filter_condition in params.filters:
        field_parts = filter_condition.field.split('.')
        field_attr = getattr(model_class, field_parts[0])

        # Handle nested fields (relationships)
        for part in field_parts[1:]:
            field_attr = getattr(field_attr, part)

        operator = filter_condition.operator
        value = filter_condition.value

        if operator == FilterOperator.EQ:
            filter_conditions.append(field_attr == value)
        elif operator == FilterOperator.NE:
            filter_conditions.append(field_attr != value)
        elif operator == FilterOperator.GT:
            filter_conditions.append(field_attr > value)
        elif operator == FilterOperator.GE:
            filter_conditions.append(field_attr >= value)
        elif operator == FilterOperator.LT:
            filter_conditions.append(field_attr < value)
        elif operator == FilterOperator.LE:
            filter_conditions.append(field_attr <= value)
        elif operator == FilterOperator.IN:
            filter_conditions.append(field_attr.in_(value.split(',')))
        elif operator == FilterOperator.NIN:
            filter_conditions.append(~field_attr.in_(value.split(',')))
        elif operator == FilterOperator.CONTAINS:
            filter_conditions.append(field_attr.contains(value))
        elif operator == FilterOperator.ICONTAINS:
            filter_conditions.append(func.lower(field_attr).contains(value.lower()))
        elif operator == FilterOperator.STARTS_WITH:
            filter_conditions.append(field_attr.startswith(value))
        elif operator == FilterOperator.ENDS_WITH:
            filter_conditions.append(field_attr.endswith(value))
        elif operator == FilterOperator.IS_NULL:
            filter_conditions.append(field_attr.is_(None))
        elif operator == FilterOperator.IS_NOT_NULL:
            filter_conditions.append(field_attr.isnot(None))
        elif operator == FilterOperator.BETWEEN:
            # Assume value is "min,max"
            min_val, max_val = value.split(',', 1)
            filter_conditions.append(and_(field_attr >= min_val, field_attr <= max_val))

    if filter_conditions:
        query = query.filter(and_(*filter_conditions))

    return query


def apply_search(query: SQLAlchemyQuery, params: SearchParams, model_class: Any) -> SQLAlchemyQuery:
    """Apply search to SQLAlchemy query"""
    if not params.query or not params.fields:
        return query

    search_conditions = []
    for field_name in params.fields:
        field_parts = field_name.split('.')
        field_attr = getattr(model_class, field_parts[0])

        # Handle nested fields (relationships)
        for part in field_parts[1:]:
            field_attr = getattr(field_attr, part)

        if params.fuzzy:
            # Simple fuzzy search using ILIKE (PostgreSQL) or LIKE with wildcards
            search_conditions.append(func.lower(field_attr).contains(params.query.lower()))
        else:
            search_conditions.append(field_attr.contains(params.query))

    if search_conditions:
        query = query.filter(or_(*search_conditions))

    return query


def apply_query_params(
    query: SQLAlchemyQuery,
    params: QueryParams,
    model_class: Any
) -> Tuple[SQLAlchemyQuery, PaginationParams]:
    """Apply all query parameters to SQLAlchemy query"""
    # Apply filtering first
    query = apply_filtering(query, params.filtering, model_class)

    # Apply search
    query = apply_search(query, params.search, model_class)

    # Apply sorting
    query = apply_sorting(query, params.sorting, model_class)

    # Apply pagination last
    query, pagination = apply_pagination(query, params.pagination)

    return query, pagination


# FastAPI dependency for query parameters
def get_query_params(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort: Optional[str] = Query(None, description="Sort fields (e.g., 'field1:asc,field2:desc')"),
    search: Optional[str] = Query(None, description="Search query"),
    search_fields: Optional[str] = Query(None, description="Fields to search in (comma-separated)"),
    fuzzy: bool = Query(False, description="Enable fuzzy search"),
) -> QueryParams:
    """FastAPI dependency to get query parameters"""
    return QueryParams.from_request(
        page=page,
        per_page=per_page,
        sort=sort,
        search=search,
        search_fields=search_fields,
        fuzzy=fuzzy
    )


# Utility functions for cursor-based pagination
def encode_cursor(value: Any) -> str:
    """Encode a value to use as a cursor"""
    import base64
    import json
    return base64.b64encode(json.dumps(value).encode()).decode()


def decode_cursor(cursor: str) -> Any:
    """Decode a cursor value"""
    import base64
    import json
    try:
        return json.loads(base64.b64decode(cursor).decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor")


def apply_cursor_pagination(
    query: SQLAlchemyQuery,
    params: CursorPaginationParams,
    cursor_field: str,
    model_class: Any
) -> Tuple[SQLAlchemyQuery, Optional[str], Optional[str]]:
    """Apply cursor-based pagination"""
    cursor_field_attr = getattr(model_class, cursor_field)

    if params.cursor:
        cursor_value = decode_cursor(params.cursor)
        if params.direction == "forward":
            query = query.filter(cursor_field_attr > cursor_value)
        else:
            query = query.filter(cursor_field_attr < cursor_value)

    # Order by cursor field
    if params.direction == "forward":
        query = query.order_by(asc(cursor_field_attr))
    else:
        query = query.order_by(desc(cursor_field_attr))

    # Limit results
    query = query.limit(params.limit + 1)  # +1 to check if there are more results

    return query, None, None  # Simplified - would need to implement next/prev cursor logic