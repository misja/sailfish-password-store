"""Stage all recipe inputs from synthetic public-source records; reject drift."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

class SourceStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sailfish-staging-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in ("tools", "sources", "evidence", "rpm", "runtime", "patches"):
            (self.root / directory).mkdir()
        shutil.copyfile(PROJECT / "tools/prepare-package.py", self.root / "tools/prepare-package.py")
        self.lock = json.loads((PROJECT / "sources.lock.json").read_text())
        for component in ("pass", "tree", "pass_otp", "oath_toolkit"):
            entry = self.lock[component]
            filename = entry.get("archive") or f"pass-otp-{entry['version']}.tar.gz"
            data = ("synthetic archive " + component).encode()
            (self.root / "sources" / filename).write_bytes(data)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
        notice = b"synthetic public LGPL notice"
        (self.root / "sources/oath-COPYING.LESSER").write_bytes(notice)
        self.lock["bootstrap"]["oath_lgpl_notice"]["sha256"] = hashlib.sha256(notice).hexdigest()
        (self.root / "sources.lock.json").write_text(json.dumps(self.lock))
        self.pass_record = {
            "gpg_verify_exit": 0, "verification": "signed-tag-and-git-archive", "tag_object": self.lock["pass"]["tag_object"],
            "commit": self.lock["pass"]["commit"],
            "allowed_primary_fingerprint": self.lock["pass"]["primary_fingerprint"],
            "verified_archive_sha256": self.lock["pass"]["sha256"]}
        self.write_pass_record()
        for component, record in (("tree", "tree-source.json"), ("pass_otp", "pass-otp-source.json"),
                                  ("oath_toolkit", "oath-source.json")):
            evidence = {"archive_sha256": self.lock[component]["sha256"]}
            if component == "oath_toolkit":
                evidence.update(primary_fingerprint=self.lock[component]["primary_fingerprint"],
                                signer_fingerprint=self.lock[component]["signer_fingerprint"],
                                verification="gpg-detached-signature")
            (self.root / "evidence" / record).write_text(json.dumps(evidence))
        for file in ("LICENSE", "LICENSING.md", "rpm/private-gpg.patch", "runtime/sailfish-pass",
                     "patches/pass-otp-stdin.patch", "patches/pass-otp-private-backend.patch",
                     "sources/pass-release-key.asc"):
            (self.root / file).write_text("synthetic public input: " + file)

    def write_pass_record(self):
        (self.root / "evidence/pass-tag-verification.json").write_text(json.dumps(self.pass_record))

    def stage(self):
        return subprocess.run([sys.executable, str(self.root / "tools/prepare-package.py")],
                              capture_output=True, text=True)

    def test_all_recipe_support_files_staged(self):
        result = self.stage()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("private-gpg.patch", "sailfish-pass", "sources.lock.json", "LICENSE",
                     "LICENSING.md", "pass-otp-stdin.patch", "pass-otp-private-backend.patch",
                     "pass-tag-verification.json", "tree-source.json", "oath-source.json"):
            self.assertTrue((self.root / "sources" / name).is_file(), name)

    def test_failed_tag_verification_prevents_staging(self):
        self.pass_record["gpg_verify_exit"] = 1
        self.write_pass_record()
        result = self.stage()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "sources/private-gpg.patch").exists())

    def test_wrong_tag_object_prevents_staging(self):
        self.pass_record["tag_object"] = "0" * 40
        self.write_pass_record()
        self.assertNotEqual(self.stage().returncode, 0)
        self.assertFalse((self.root / "sources/private-gpg.patch").exists())

    def test_corrupt_oath_archive_prevents_staging(self):
        archive = self.root / "sources" / self.lock["oath_toolkit"]["archive"]
        archive.write_bytes(b"corrupt synthetic public archive")
        self.assertNotEqual(self.stage().returncode, 0)
        self.assertFalse((self.root / "sources/private-gpg.patch").exists())

if __name__ == "__main__":
    unittest.main()
