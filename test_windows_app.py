"""Desktop tests run without a tray, watch, or Windows registry."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import windows_app as app


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, SMARTMIBAND_DATA_DIR=self.temp.name)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_config_preserved_and_port(self):
        path = app.prepare_config()
        cfg = json.loads(path.read_text())
        self.assertEqual(cfg['host'], '127.0.0.1')
        cfg.update(http_port=9123, auth_key='ab' * 16)
        path.write_text(json.dumps(cfg))
        self.assertEqual(app.prepare_config().read_text(), json.dumps(cfg))
        self.assertEqual(app.dashboard_url(), 'http://127.0.0.1:9123')

    def test_frozen_command_does_not_run_python_script(self):
        with patch.object(app.sys, 'frozen', True, create=True):
            self.assertEqual(app.service_command(), [app.sys.executable, '--service'])

    def test_invalid_key_does_not_spawn(self):
        c = app.ServiceController()
        with patch.object(app.subprocess, 'Popen') as popen:
            with self.assertRaises(ValueError):
                c.start()
            popen.assert_not_called()

    def test_start_idempotent_stop_owned_child(self):
        path = app.prepare_config()
        cfg = json.loads(path.read_text())
        cfg['auth_key'] = 'ab' * 16
        path.write_text(json.dumps(cfg))
        child = Mock()
        child.poll.return_value = None
        c = app.ServiceController()
        with patch.object(app.subprocess, 'Popen', return_value=child) as popen:
            c.start()
            c.start()
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(popen.call_args.kwargs['env']['SMARTMIBAND_DATA_DIR'], self.temp.name)
            c.stop()
            child.wait.assert_called_once_with(timeout=12)
            child.terminate.assert_not_called()
            self.assertFalse(c.stop_file.exists())

    def test_hung_child_fallback(self):
        c = app.ServiceController()
        c.process = Mock()
        c.process.poll.return_value = None
        c.process.wait.side_effect = [app.subprocess.TimeoutExpired('service', 12), 0]
        c.stop()
        c.process.terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
