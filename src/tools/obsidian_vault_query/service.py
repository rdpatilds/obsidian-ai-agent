"""Service layer for Obsidian Vault Query tool."""

import time
from pathlib import Path
from typing import Any, assert_never

import aiofiles  # type: ignore[import-untyped]

from src.shared.logging import get_logger
from src.shared.obsidian_parsers import (
    extract_frontmatter_safely,
    get_all_tags,
)
from src.shared.response_formatter import (
    format_note_response,
    truncate_with_guidance,
)
from src.shared.vault_security import is_path_allowed
from src.tools.obsidian_vault_query.schemas import (
    QueryMode,
    QueryRequest,
    QueryResponse,
    QueryResult,
)


logger = get_logger(__name__)


async def query_vault_service(
    request: QueryRequest,
    vault_path: str,
) -> QueryResponse:
    """Execute vault query across multiple search dimensions.

    Args:
        request: QueryRequest with query details and filters.
        vault_path: Absolute path to Obsidian vault root.

    Returns:
        QueryResponse with matching results and metadata.
    """
    start_time = time.perf_counter()
    vault_root = Path(vault_path)

    logger.info(
        "vault_query_started",
        mode=request.mode.value,
        query=request.query[:100],
        max_results=request.max_results,
    )

    # Execute query based on mode
    if request.mode == QueryMode.FULLTEXT:
        results = await _query_fulltext(vault_root, request)
    elif request.mode == QueryMode.PROPERTIES:
        results = await _query_properties(vault_root, request)
    elif request.mode == QueryMode.TAGS:
        results = await _query_tags(vault_root, request)
    elif request.mode == QueryMode.DATAVIEW:
        results = await _query_dataview(vault_root, request)
    else:
        assert_never(request.mode)

    # Apply pagination
    total_found = len(results)
    paginated_results, guidance_message = truncate_with_guidance(
        results[request.offset :], request.max_results
    )

    # Convert to QueryResult objects
    query_results = [
        QueryResult(
            path=r["path"],
            title=r["title"],
            excerpt=r.get("excerpt"),
            match_count=r.get("match_count"),
            metadata=r.get("metadata", {}),
        )
        for r in paginated_results
    ]

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "vault_query_completed",
        mode=request.mode.value,
        total_found=total_found,
        returned=len(query_results),
        duration_ms=duration_ms,
    )

    return QueryResponse(
        results=query_results,
        total_found=total_found,
        truncated=len(results) > request.max_results,
        query=request.query,
        mode=request.mode,
        guidance_message=guidance_message if guidance_message else None,
    )


async def _query_fulltext(
    vault_root: Path, request: QueryRequest
) -> list[dict[str, Any]]:
    """Search vault for full-text matches."""
    query_lower = request.query if request.case_sensitive else request.query.lower()
    results: list[dict[str, Any]] = []

    # Scan all markdown files
    for note_path in vault_root.rglob("*.md"):
        if not is_path_allowed(str(note_path)):
            continue

        try:
            async with aiofiles.open(note_path, encoding="utf-8") as f:
                content = await f.read()

            # Parse frontmatter
            metadata, body = extract_frontmatter_safely(content)

            # Search in body
            search_text = body if request.case_sensitive else body.lower()
            match_count = search_text.count(query_lower)

            if match_count > 0:
                # Extract excerpt around first match
                match_pos = search_text.find(query_lower)
                excerpt_start = max(0, match_pos - 50)
                excerpt_end = min(len(body), match_pos + len(request.query) + 50)
                excerpt = body[excerpt_start:excerpt_end].strip()

                # Format result based on response_format
                note_data = {
                    "title": note_path.stem,
                    "content": body,
                    "frontmatter": metadata,
                    "tags": metadata.get("tags", []),
                    "path": str(note_path.relative_to(vault_root)),
                }
                formatted = format_note_response(note_data, request.response_format)

                results.append(
                    {
                        "path": str(note_path.relative_to(vault_root)),
                        "title": note_path.stem,
                        "excerpt": f"...{excerpt}...",
                        "match_count": match_count,
                        "metadata": formatted,
                    }
                )

        except Exception as e:
            logger.warning(
                "note_read_failed",
                path=str(note_path),
                error=str(e),
            )
            continue

    # Sort by match count (descending)
    results.sort(key=lambda x: x.get("match_count", 0), reverse=True)

    return results


async def _query_properties(
    vault_root: Path, request: QueryRequest
) -> list[dict[str, Any]]:
    """Filter notes by frontmatter properties."""
    if not request.property_filters:
        logger.warning("properties_query_empty_filters")
        return []

    results: list[dict[str, Any]] = []

    # Scan all markdown files
    for note_path in vault_root.rglob("*.md"):
        if not is_path_allowed(str(note_path)):
            continue

        try:
            async with aiofiles.open(note_path, encoding="utf-8") as f:
                content = await f.read()

            metadata, body = extract_frontmatter_safely(content)

            # Check if properties match filters
            if _matches_property_filters(metadata, request.property_filters):
                note_data = {
                    "title": note_path.stem,
                    "content": body,
                    "frontmatter": metadata,
                    "tags": metadata.get("tags", []),
                    "path": str(note_path.relative_to(vault_root)),
                }
                formatted = format_note_response(note_data, request.response_format)

                results.append(
                    {
                        "path": str(note_path.relative_to(vault_root)),
                        "title": note_path.stem,
                        "metadata": formatted,
                    }
                )

        except Exception as e:
            logger.warning("note_read_failed", path=str(note_path), error=str(e))
            continue

    return results


async def _query_tags(
    vault_root: Path, request: QueryRequest
) -> list[dict[str, Any]]:
    """Filter notes by tags."""
    if not request.tag_filters:
        logger.warning("tags_query_empty_filters")
        return []

    results: list[dict[str, Any]] = []

    # Scan all markdown files
    for note_path in vault_root.rglob("*.md"):
        if not is_path_allowed(str(note_path)):
            continue

        try:
            async with aiofiles.open(note_path, encoding="utf-8") as f:
                content = await f.read()

            metadata, body = extract_frontmatter_safely(content)
            note_tags = get_all_tags(body, metadata)

            # Check if any requested tag is present (OR logic)
            matching_tags = [tag for tag in request.tag_filters if tag in note_tags]

            if matching_tags:
                note_data = {
                    "title": note_path.stem,
                    "content": body,
                    "frontmatter": metadata,
                    "tags": note_tags,
                    "path": str(note_path.relative_to(vault_root)),
                }
                formatted = format_note_response(note_data, request.response_format)

                results.append(
                    {
                        "path": str(note_path.relative_to(vault_root)),
                        "title": note_path.stem,
                        "metadata": formatted,
                        "matching_tags": matching_tags,
                    }
                )

        except Exception as e:
            logger.warning("note_read_failed", path=str(note_path), error=str(e))
            continue

    return results


async def _query_dataview(
    vault_root: Path, request: QueryRequest
) -> list[dict[str, Any]]:
    """Execute Dataview query (basic fallback implementation)."""
    logger.warning(
        "dataview_fallback",
        message="Full Dataview support requires Local REST API. Using basic fallback.",
    )

    # Basic fallback: parse simple "FROM #tag" queries
    query_lower = request.query.lower()
    if "from #" in query_lower:
        # Extract tag from "LIST FROM #tag" or "TABLE FROM #tag"
        tag_start = query_lower.find("from #") + 6
        tag_end = query_lower.find(" ", tag_start)
        if tag_end == -1:
            tag_end = len(query_lower)
        tag = request.query[tag_start:tag_end].strip()

        # Use tag query
        tag_request = QueryRequest(
            query=tag,
            mode=QueryMode.TAGS,
            tag_filters=[tag],
            max_results=request.max_results,
            response_format=request.response_format,
        )
        return await _query_tags(vault_root, tag_request)

    logger.error("dataview_unsupported_query", query=request.query)
    return []


def _matches_property_filters(
    metadata: dict[str, Any], filters: dict[str, Any]
) -> bool:
    """Check if metadata matches property filters.

    Supports:
    - Direct equality: {"status": "active"}
    - Operators: {"priority": {"$gt": 5, "$lt": 10}}
    """
    for key, expected_value in filters.items():
        if key not in metadata:
            return False

        actual_value = metadata[key]

        # Handle operator syntax
        if isinstance(expected_value, dict):
            for operator, op_value in expected_value.items():
                if (operator == "$gt" and not (actual_value > op_value)) or (operator == "$gte" and not (actual_value >= op_value)):
                    return False
                if (operator == "$lt" and not (actual_value < op_value)) or (operator == "$lte" and not (actual_value <= op_value)) or (operator == "$ne" and actual_value == op_value) or (operator == "$eq" and actual_value != op_value):
                    return False
        # Direct equality
        elif actual_value != expected_value:
            return False

    return True
