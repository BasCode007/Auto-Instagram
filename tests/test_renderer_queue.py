import json, os, sys, tempfile, unittest, importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class QueueTests(unittest.TestCase):
    def test_pop_in_order_then_exhausted(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as state:
            json.dump([{"id": "a", "script": "A", "hook": "A"}, {"id": "b", "script": "B"}, {"id": "c"}],
                      open(os.path.join(content, "queue.json"), "w"))
            os.environ["CONTENT_DIR"], os.environ["STATE_DIR"] = content, state
            srv = importlib.import_module("renderer.server"); importlib.reload(srv)
            first = srv.queue_pop(); second = srv.queue_pop(); third = srv.queue_pop()
            self.assertEqual(first["id"], "a"); self.assertTrue(first["queued"])
            self.assertEqual(json.loads(first["choices"][0]["message"]["content"])["script"], "A")
            self.assertNotIn("id", json.loads(first["choices"][0]["message"]["content"]))
            self.assertEqual(second["id"], "b")
            self.assertFalse(third["queued"])                      # "c" has no script, so it is skipped
            self.assertEqual(json.load(open(os.path.join(state, "queue_state.json")))["used"], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
