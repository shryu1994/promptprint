import unittest
import tests.conftest_path  # noqa: F401  (sys.path 설정)


class SmokeTest(unittest.TestCase):
    def test_package_imports(self):
        import wami
        self.assertEqual(wami.__version__, "0.2.0")
