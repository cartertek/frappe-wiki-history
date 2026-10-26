import unittest

from wiki_history.integration import inject_history_link


class FakeResponse:
    def __init__(self, html, status=200, content_type="text/html; charset=utf-8"):
        self.body = html
        self.status_code = status
        self.content_type = content_type
        self.headers = {"ETag": "abc"}

    def get_data(self, as_text=False):
        return self.body if as_text else self.body.encode()

    def set_data(self, html):
        self.body = html


class IntegrationTests(unittest.TestCase):
    def test_only_wiki_shell_receives_one_asset_reference(self):
        from types import SimpleNamespace
        response = FakeResponse("<html><body><div id='app'></div></body></html>")
        request = SimpleNamespace(path="/wiki-app/spaces/space/page/abc")
        inject_history_link(response, request)
        inject_history_link(response, request)
        self.assertEqual(response.body.count("history_link.js"), 1)
        self.assertNotIn("ETag", response.headers)

    def test_other_routes_and_responses_unchanged(self):
        from types import SimpleNamespace
        for path in ("/", "/wiki-history", "/api/method/wiki_history.api.get_page_history"):
            response = FakeResponse("<html><body></body></html>")
            inject_history_link(response, SimpleNamespace(path=path))
            self.assertNotIn("history_link.js", response.body)
        response = FakeResponse("{}", content_type="application/json")
        inject_history_link(response, SimpleNamespace(path="/wiki-app"))
        self.assertEqual(response.body, "{}")


if __name__ == "__main__":
    unittest.main()
