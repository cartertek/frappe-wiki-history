# Frappe Wiki History

A standalone Frappe v16 application that adds **History** to every page in
[Frappe Wiki v3](https://github.com/frappe/wiki). No Wiki source files,
Vue components, DocTypes, templates, or revision-writing code are modified.

## Features

- Context-specific **History** link in the existing Wiki page toolbar,
  updated as users navigate between pages.
- Wikipedia-style history of published revisions **that changed that page**,
  showing author, timestamp, edit message, and changed properties.
- Open saved revisions; compare with the previous revision or select any two
  versions for a line-numbered diff.
- Highlights added and removed text, page metadata, moves, order, and publication.
- Supports full and overlay revisions; identifies the page by Wiki doc_key.
- Read-only APIs with Wiki Space permissions.

## Install

Install Frappe Wiki v3 before this app, then get and install wiki_history with
standard Frappe bench commands. Run bench build and restart for the assets.

If backend and Nginx use separate container images, include wiki_history in
both images so its /assets/wiki_history files are served. The Job Search Platform
does this with one app manifest and image build.

On every Wiki page the **History** toolbar link opens a page-specific URL in
the custom app, at /wiki-history?space=...&page=... .

## APIs

GET-only, authenticated, and scoped to a Wiki Space:

- wiki_history.api.get_page_history(space, page, offset=0, limit=30)
- wiki_history.api.get_page_revision(space, page, revision)
- wiki_history.api.compare_page_revisions(space, page, old, new)

The page argument normally identifies the Wiki Document name. Space editors
may use a removed page's stable doc_key. Revision IDs must be in the
published main ancestry for that Wiki Space.

## Limits and compatibility

Only states actually saved by Wiki can be retrieved. Draft branches and
unmerged change requests are excluded from published revision history.
The app only reads revision records and does not alter Wiki's revision
capture logic. Diffs exceeding 12,000 lines show an explicit truncation warning.

The toolbar integration uses Frappe 16's after_request hook to load one
JavaScript asset into Wiki's standalone /wiki-app HTML. Standard Desk/website
JavaScript hooks do not load in this SPA. The History link locates Wiki's page
actions by their accessibility labels; if Wiki changes that toolbar, the API
and history viewer remain functional, but the link locator may need adjustment.

Tests: python3 -m unittest discover -s tests -v
