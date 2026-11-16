import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from audyssey.store import JobStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = JobStore(Path(self.tmp.name))

    def test_create_and_load(self):
        job, directory = self.store.create("clip.mp4", b"video")
        self.assertEqual(job.video_path, "input.mp4")
        self.assertEqual((directory / job.video_path).read_bytes(), b"video")
        self.assertEqual(self.store.load(job.id), job)

    def test_create_keeps_only_video_suffixes(self):
        for name, expected in [("a.MOV", "input.mov"), ("page.html", "input.mp4"), ("noext", "input.mp4")]:
            job, directory = self.store.create(name, b"video")
            self.assertEqual(job.video_path, expected)
            self.assertTrue((directory / expected).exists())

    def test_save_increments_version(self):
        job, _ = self.store.create("clip.mp4", b"video")
        version = job.version
        self.store.save(job)
        self.assertEqual(self.store.load(job.id).version, version + 1)

    def test_save_retries_a_temporary_file_lock(self):
        job, directory = self.store.create("clip.mp4", b"video")
        version = job.version
        replace = Path.replace
        calls = []

        def replace_after_unlock(path, target):
            calls.append(path)
            if len(calls) < 3:
                raise PermissionError("file is temporarily locked")
            return replace(path, target)

        with patch.object(Path, "replace", replace_after_unlock), patch("time.sleep"):
            self.store.save(job)

        self.assertEqual(len(calls), 3)
        self.assertEqual(self.store.load(job.id).version, version + 1)
        self.assertEqual(list(directory.glob("tmp*")), [])

    def test_failed_save_keeps_previous_version_and_cleans_temporary_file(self):
        job, directory = self.store.create("clip.mp4", b"video")
        version = job.version
        with patch.object(Path, "replace", side_effect=PermissionError("locked")), patch(
            "time.sleep"
        ), self.assertRaises(PermissionError):
            self.store.save(job)

        self.assertEqual(job.version, version)
        self.assertEqual(self.store.load(job.id).version, version)
        self.assertEqual(list(directory.glob("tmp*")), [])

    def test_job_json_uses_utf8_for_korean_text(self):
        job, directory = self.store.create("clip.mp4", b"video")
        job.error = "분리 작업을 다시 실행해 주세요"
        self.store.save(job)
        self.assertIn(job.error, (directory / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(self.store.load(job.id).error, job.error)

    def test_list_newest_first(self):
        a, _ = self.store.create("a.mp4", b"a")
        b, _ = self.store.create("b.mp4", b"b")
        os.utime(self.store.dir(a.id) / "job.json", ns=(1000000000, 1000000000))
        os.utime(self.store.dir(b.id) / "job.json", ns=(2000000000, 2000000000))
        self.assertEqual([j.id for j in self.store.list()], [b.id, a.id])
        self.store.save(a)
        self.assertEqual(self.store.list()[0].id, a.id)

    def test_resolve_rejects_traversal(self):
        job, directory = self.store.create("clip.mp4", b"video")
        (directory / "escape").symlink_to("/etc/passwd")
        for rel in ["../x", "/etc/passwd", "missing", "escape"]:
            with self.subTest(rel=rel), self.assertRaises(KeyError):
                self.store.resolve(job.id, rel)
        self.assertEqual(
            self.store.resolve(job.id, "input.mp4"), directory / "input.mp4"
        )

    def test_load_rejects_bad_id(self):
        with self.assertRaises(KeyError):
            self.store.load("../..")
