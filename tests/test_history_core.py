import unittest

from wiki_history.history_core import ancestry, changes, diff_lines, effective_item


class HistoryCoreTests(unittest.TestCase):
    def setUp(self):
        self.revisions = {
            "a": {"name": "a", "parent_revision": None, "is_overlay": 0},
            "b": {"name": "b", "parent_revision": "a", "is_overlay": 1},
            "c": {"name": "c", "parent_revision": "b", "is_overlay": 1},
            "d": {"name": "d", "parent_revision": "c", "is_overlay": 0},
        }
        self.items = {
            "a": {"title": "Initial", "content_blob": "one", "order_index": 1},
            "c": {"title": "Renamed", "content_blob": "two", "order_index": 1},
            "d": {"title": "Renamed", "content_blob": "two", "order_index": 2},
        }

    def test_nested_overlay_inherits_page(self):
        self.assertEqual(effective_item("b", self.revisions, self.items)["title"], "Initial")
        self.assertEqual(effective_item("c", self.revisions, self.items)["title"], "Renamed")

    def test_comparison_detects_content_and_metadata(self):
        old = effective_item("b", self.revisions, self.items)
        new = effective_item("c", self.revisions, self.items)
        self.assertEqual(changes(old, new), ["title", "content_blob"])
        self.assertEqual(changes(new, effective_item("d", self.revisions, self.items)), ["order_index"])

    def test_full_snapshot_without_item_is_deletion(self):
        self.assertIsNone(effective_item("d", self.revisions, {}))
        self.assertEqual(changes(self.items["a"], None), ["deleted"])
        self.assertEqual(changes(None, self.items["a"]), ["created"])

    def test_overlay_deleted_tombstone(self):
        self.items["b"] = {"is_deleted": 1}
        self.assertIsNone(effective_item("b", self.revisions, self.items))
        self.assertIsNone(effective_item("c", self.revisions, {"b": {"is_deleted": 1}}))

    def test_ancestry_and_cycle_detection(self):
        self.assertEqual([r["name"] for r in ancestry("d", self.revisions)], ["d", "c", "b", "a"])
        self.revisions["a"]["parent_revision"] = "d"
        with self.assertRaises(ValueError):
            ancestry("d", self.revisions)

    def test_diff_line_numbers_and_added_removed(self):
        lines, truncated = diff_lines("one\ntwo\n", "one\nthree\n")
        self.assertFalse(truncated)
        self.assertEqual([(r["kind"], r["old"], r["new"]) for r in lines],
                         [("context", 1, 1), ("remove", 2, None), ("add", None, 2)])

    def test_diff_escapes_in_frontend_not_here(self):
        lines, _ = diff_lines("<script>x</script>", "<script>y</script>")
        self.assertTrue(any("<script>" in row["text"] for row in lines))

    def test_empty_diff(self):
        self.assertEqual(diff_lines("same", "same")[0], [])


if __name__ == "__main__":
    unittest.main()
