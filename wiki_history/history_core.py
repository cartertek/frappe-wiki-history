"""Pure revision comparison logic, deliberately independent of Frappe.

Overlay revisions inherit items from their parent. A full revision is a
complete snapshot; an absent item in a full revision is a deletion.
"""
from difflib import SequenceMatcher

FIELDS = (
    "title", "slug", "route", "is_group", "is_tab", "tab_icon",
    "is_published", "is_external_link", "external_url",
    "parent_key", "order_index", "content_blob",
)


def ancestry(main, revisions):
    """Return the main branch newest first, with cycles rejected."""
    result, visited = [], set()
    cursor = main
    while cursor:
        if cursor in visited:
            raise ValueError("Revision ancestry contains a cycle")
        visited.add(cursor)
        revision = revisions.get(cursor)
        if not revision:
            raise ValueError(f"Missing revision in ancestry: {cursor}")
        result.append(revision)
        cursor = revision.get("parent_revision")
    return result


def effective_item(revision, revisions, items, cache=None):
    """Return a single page's snapshot at revision, resolving overlays."""
    if not revision:
        return None
    if cache is None:
        cache = {}
    if revision in cache:
        return cache[revision]
    info = revisions.get(revision)
    if info is None:
        raise ValueError(f"Unknown revision: {revision}")
    item = items.get(revision)
    if item is None and info.get("is_overlay"):
        # Check ancestry for corruption before recursion.
        seen, current = {revision}, info.get("parent_revision")
        while current:
            if current in seen:
                raise ValueError("Overlay ancestry contains a cycle")
            seen.add(current)
            ancestor = revisions.get(current)
            if ancestor is None:
                raise ValueError(f"Missing overlay parent: {current}")
            if current in cache:
                item = cache[current]
                break
            if current in items:
                item = items[current]
                break
            if not ancestor.get("is_overlay"):
                break
            current = ancestor.get("parent_revision")
    cache[revision] = None if item is None or item.get("is_deleted") else item
    return cache[revision]


def changes(old, new):
    """Return names of modified snapshot fields, including content."""
    if old is None and new is None:
        return []
    if old is None:
        return ["created"]
    if new is None:
        return ["deleted"]
    return [field for field in FIELDS if old.get(field) != new.get(field)]


def diff_lines(old_content, new_content, context=3, max_rows=12000):
    """Return grouped, numbered, unified diff lines with safe, plain text."""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    matcher = SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    result, truncated = [], False
    for group in matcher.get_grouped_opcodes(context):
        if result:
            result.append({"kind": "separator", "old": None, "new": None, "text": ""})
        for tag, i1, i2, j1, j2 in group:
            if tag in ("equal", "replace", "delete"):
                for i in range(i1, i2):
                    result.append({
                        "kind": "context" if tag == "equal" else "remove",
                        "old": i + 1, "new": j1 + (i - i1) + 1 if tag == "equal" else None,
                        "text": old_lines[i],
                    })
            if tag in ("replace", "insert"):
                for j in range(j1, j2):
                    result.append({"kind": "add", "old": None, "new": j + 1, "text": new_lines[j]})
            if len(result) > max_rows:
                result = result[:max_rows]
                truncated = True
                break
        if truncated:
            break
    return result, truncated
