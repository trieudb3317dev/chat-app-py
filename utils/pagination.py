from typing import Any, Dict


def paginate(items: list, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": [
            {
                "id": item.id,
                "full_name": item.full_name,
                "email": item.email,
                "created_at": item.created_at,
                "is_active": item.is_active,
            }
            for item in items[start:end]
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "start_index": start,
        "end_index": min(end, total),
    }
