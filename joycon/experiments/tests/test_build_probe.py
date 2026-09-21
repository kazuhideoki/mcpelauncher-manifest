import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('build_probe', Path(__file__).parents[1] / 'build_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class SourceCopyTests(unittest.TestCase):
    def test_preserves_android_dangling_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            (source / '.clang-format').symlink_to('../missing/.clang-format')
            (source / 'input.cpp').write_text('source')
            destination = Path(tmp) / 'copied'
            probe.copy_sources(source, destination)
            self.assertTrue((destination / '.clang-format').is_symlink())
            self.assertEqual((destination / '.clang-format').readlink(), Path('../missing/.clang-format'))
            self.assertEqual((destination / 'input.cpp').read_text(), 'source')

    def test_accepts_header_only_json_and_rejects_missing_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            deps = Path(tmp)
            glfw = deps / 'glfw3_ext-src'
            glfw.mkdir()
            (glfw / 'CMakeLists.txt').touch()
            header = deps / 'nlohmann_json_ext-src/include/nlohmann/json.hpp'
            header.parent.mkdir(parents=True)
            header.touch()
            self.assertEqual(len(probe.cached_dependency_options(deps)), 2)
            header.unlink()
            with self.assertRaisesRegex(ValueError, 'json.hpp'):
                probe.cached_dependency_options(deps)


if __name__ == '__main__':
    unittest.main()
