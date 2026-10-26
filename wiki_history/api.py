"""Read-only page history and diff API for Frappe Wiki v3.

Only revisions on the published main ancestry are exposed. Working branches
and unrelated change requests are deliberately excluded from page history.
All reads are scoped to a Wiki Space with server-side authorization.
"""
from __future__ import annotations

import frappe
from frappe import _

from wiki_history.history_core import FIELDS, ancestry, changes, diff_lines, effective_item

REVISION_FIELDS = [
    "name", "parent_revision", "wiki_space", "created_at", "created_by",
    "message", "is_overlay", "is_working", "change_request",
]
ITEM_FIELDS = ["revision", "doc_key", "is_deleted", *FIELDS]
MAX_PAGE_SIZE = 100


def _load(space, page):
    """Validate access before any historical items or blobs are accessed."""
    from wiki.permissions import can_read_space, can_write_space

    if frappe.session.user == "Guest":
        frappe.throw(_("Sign in to view page history"), frappe.PermissionError)
    if not frappe.db.exists("Wiki Space", space) or not can_read_space(space):
        frappe.throw(_("Not permitted to view this Wiki Space"), frappe.PermissionError)
    current = frappe.db.get_value(
        "Wiki Document", page, ["name", "doc_key", "title", "wiki_space", "is_published"],
        as_dict=True,
    )
    if current and current.wiki_space != space:
        frappe.throw(_("Page is not in this Wiki Space"), frappe.PermissionError)
    if not current:
        # A removed page can still be inspected by its stable doc_key, but only
        # by space editors; otherwise historical unpublished data could leak.
        if not can_write_space(space):
            frappe.throw(_("Page not available"), frappe.PermissionError)
        current = frappe.db.get_value(
            "Wiki Document", {"wiki_space": space, "doc_key": page},
            ["name", "doc_key", "title", "wiki_space", "is_published"], as_dict=True,
        )
        if not current:
            current = frappe._dict(name=None, doc_key=page, title=page, wiki_space=space)
    elif not current.is_published and not can_write_space(space):
        frappe.throw(_("Not permitted to view unpublished page history"), frappe.PermissionError)

    head = frappe.db.get_value("Wiki Space", space, "main_revision")
    all_revisions = frappe.get_all(
        "Wiki Revision", filters={"wiki_space": space},
        fields=REVISION_FIELDS, limit_page_length=0,
    )
    by_id = {r.name: r for r in all_revisions}
    chain = ancestry(head, by_id) if head else []
    # If an unexpected working revision is on the main chain, do not expose it.
    chain = [r for r in chain if not r.is_working]
    ids = [r.name for r in chain]
    item_map = {}
    for start in range(0, len(ids), 250):
        for item in frappe.get_all(
            "Wiki Revision Item",
            filters={"revision": ["in", ids[start:start + 250]], "doc_key": current.doc_key},
            fields=ITEM_FIELDS, limit_page_length=0,
        ):
            item_map[item.revision] = item

    return current, chain, by_id, item_map


def _history(space, page):
    current, chain, revisions, items = _load(space, page)
    cache = {}
    result = []
    for revision in chain:
        before = effective_item(revision.parent_revision, revisions, items, cache)
        after = effective_item(revision.name, revisions, items, cache)
        modified = changes(before, after)
        if not modified:
            continue
        result.append({
            "revision": revision.name,
            "parent_revision": revision.parent_revision,
            "date": str(revision.created_at or ""),
            "author": revision.created_by,
            "message": revision.message or "",
            "fields": modified,
            "kind": "created" if before is None else "deleted" if after is None else "edited",
        })
    return current, result, chain, revisions, items


def _page_dict(doc):
    return {"name": doc.name, "doc_key": doc.doc_key, "title": doc.title}


def _approved_revision(revision, chain):
    if revision not in {r.name for r in chain}:
        frappe.throw(_("Revision is not in this Wiki Space's published history"),
                     frappe.PermissionError)


def _serialize(item):
    if not item:
        return None
    return {field: item.get(field) for field in FIELDS if field != "content_blob"}


def _content(item):
    if not item or not item.get("content_blob"):
        return ""
    return frappe.db.get_value("Wiki Content Blob", item["content_blob"], "content") or ""


@frappe.whitelist(methods=["GET"])
def get_page_history(space: str, page: str, offset=0, limit=30):
    current, records, *_ = _history(space, page)
    try:
        offset, limit = int(offset), int(limit)
    except (ValueError, TypeError):
        frappe.throw(_("Invalid pagination arguments"))
    if offset < 0 or not 1 <= limit <= MAX_PAGE_SIZE:
        frappe.throw(_("Invalid pagination arguments"))
    return {
        "page": _page_dict(current), "space": space, "total": len(records),
        "rows": records[offset:offset + limit],
        "next_offset": offset + limit if offset + limit < len(records) else None,
    }


@frappe.whitelist(methods=["GET"])
def get_page_revision(space: str, page: str, revision: str):
    current, _, chain, revisions, items = _history(space, page)
    _approved_revision(revision, chain)
    item = effective_item(revision, revisions, items)
    if not item:
        frappe.throw(_("Page did not exist at this revision"))
    rev = revisions[revision]
    return {
        "page": _page_dict(current), "space": space, "revision": revision,
        "date": str(rev.created_at or ""), "author": rev.created_by,
        "message": rev.message or "",
        "metadata": _serialize(item), "content": _content(item),
    }


@frappe.whitelist(methods=["GET"])
def compare_page_revisions(space: str, page: str, old: str, new: str):
    current, _, chain, revisions, items = _history(space, page)
    # A synthetic empty base represents creation in the very first revision.
    _approved_revision(new, chain)
    if old:
        _approved_revision(old, chain)
    old_item = effective_item(old, revisions, items)
    new_item = effective_item(new, revisions, items)
    old_content, new_content = _content(old_item), _content(new_item)
    lines, truncated = diff_lines(old_content, new_content)
    modified = changes(old_item, new_item)
    metadata = [
        {"field": field, "old": old_item.get(field) if old_item else None,
         "new": new_item.get(field) if new_item else None}
        for field in modified if field not in ("content_blob", "created", "deleted")
    ]
    return {
        "page": _page_dict(current), "space": space,
        "old": old or None, "new": new,
        "modified_fields": modified, "metadata_changes": metadata,
        "old_metadata": _serialize(old_item), "new_metadata": _serialize(new_item),
        "lines": lines, "truncated": truncated,
    }
