import os
import subprocess
import unittest
from unittest.mock import patch
from backend.app import create_app
from backend.services.host_scan import scan

class HostScanTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_disabled_and_remote_access_blocked(self):
        with patch.dict(os.environ, {"ENABLE_HOST_SCAN": "0"}):
            self.assertEqual(self.client.post("/api/host-scan", json={"consent": True}).status_code, 403)
        self.assertEqual(self.client.get("/api/host-scan/status", environ_overrides={"REMOTE_ADDR": "192.168.1.4"}).status_code, 403)
        self.assertEqual(self.client.get("/api/host-scan/status", headers={"Host": "evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/api/host-scan/status", headers={"Origin": "https://evil.example"}).status_code, 403)

    @patch.dict(os.environ, {"ENABLE_HOST_SCAN": "1"})
    @patch("backend.route.host_scan.scan", return_value={"findings": []})
    def test_token_consent_and_success(self, scanner):
        token = self.client.get("/api/host-scan/status").json["token"]
        self.assertEqual(self.client.post("/api/host-scan", json={"consent": True}).status_code, 403)
        headers = {"X-Scan-Token": token}
        self.assertEqual(self.client.post("/api/host-scan", headers=headers, json={"consent": False}).status_code, 400)
        scanner.assert_not_called()
        self.assertEqual(self.client.post("/api/host-scan", headers=headers, json={"consent": True}).status_code, 200)
        scanner.assert_called_once()

    @patch("backend.services.host_scan.platform.system", return_value="Windows")
    @patch("backend.services.host_scan.subprocess.run")
    def test_real_check_evaluation_and_unknowns(self, run, system):
        run.side_effect = [
            subprocess.CompletedProcess([], 0, '{"AntivirusEnabled":true,"RealTimeProtectionEnabled":true,"AntivirusSignatureAge":1}'),
            subprocess.CompletedProcess([], 0, '[{"Name":"Public","Enabled":false}]'),
            subprocess.TimeoutExpired("powershell.exe", 15),
            subprocess.CompletedProcess([], 0, '{"EnableLUA":1}'),
            subprocess.CompletedProcess([], 0, '{"AgeDays":60}')]
        result = scan()
        self.assertEqual([r["status"] for r in result["findings"]], ["pass", "warning", "unknown", "pass", "warning"])
        self.assertEqual(result["summary"], {"pass": 2, "warning": 2, "unknown": 1})
        self.assertEqual(run.call_count, 5)
        for call in run.call_args_list:
            self.assertEqual(call.args[0][0], "powershell.exe")
            self.assertNotIn("shell", call.kwargs)

    @patch("backend.services.host_scan.platform.system", return_value="Linux")
    @patch("backend.services.host_scan.subprocess.run")
    def test_docker_linux_cannot_claim_to_scan_windows(self, run, system):
        with self.assertRaises(ValueError):
            scan()
        run.assert_not_called()
