"""Inject a single custom-app asset in Frappe Wiki's standalone Vue shell.

Normal app_include_js and web_include_js do not run on /wiki-app. Frappe's
after_request hook is the supported integration point. No Wiki files change.
"""


def inject_history_link(response, request):
    if request.path != "/wiki-app" and not request.path.startswith("/wiki-app/"):
        return
    if response.status_code != 200 or "text/html" not in response.content_type:
        return

    html = response.get_data(as_text=True)
    marker = '/assets/wiki_history/js/history_link.js'
    if marker in html or "</body>" not in html:
        return
    response.set_data(
        html.replace("</body>", f'<script defer src="{marker}"></script></body>', 1)
    )
    response.headers.pop("ETag", None)
