"""验证发布包完整性、可重现校验值和源码目录隔离。"""
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_modules',root/'build/package-modules.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PackageTests(unittest.TestCase):
    def test_complete_reproducible_package_excludes_development_files(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'source';compiled=base/'compiled';output=base/'output'
            for folder in [source,compiled,output]:folder.mkdir()
            manifest={'id':'synthetic','name':'合成模块','version':'1.2.3','moduleApi':1,'engines':{'framework':'>=0.1.8 <0.2.0'},'runtime':{'entry':'index.mjs','files':['resources']}}
            (source/'courseflow.module.json').write_text(json.dumps(manifest))
            for name in ['LICENSE','README.md','SOURCE.json']:(source/name).write_text('{}' if name=='SOURCE.json' else '合成内容')
            (source/'resources').mkdir();(source/'resources/data.txt').write_text('资源')
            (source/'resources/__pycache__').mkdir();(source/'resources/__pycache__/cache.pyc').write_bytes(b'cache')
            (source/'secret.key').write_bytes(b'must not be published')
            (source/'index.mjs').write_text('stale output')
            (compiled/'index.mjs').write_text('console.log("compiled")')
            info={'repository':'Course-Flow-Lab/synthetic','commit':'a'*40,'target':'node24','requirements':'Node.js 24+'}
            first=module.pack(source,compiled,info,output)
            archive=output/Path(first['file']).name
            before=archive.read_bytes();second=module.pack(source,compiled,info,output)
            self.assertEqual(archive.read_bytes(),before);self.assertEqual(first['sha256'],second['sha256'])
            with tarfile.open(archive) as package:
                self.assertEqual(set(package.getnames()),{'package/'+name for name in ['INSTALL.md','LICENSE','README.md','SOURCE.json','courseflow.module.json','index.mjs','resources/data.txt']})
                self.assertEqual(package.extractfile('package/index.mjs').read(),b'console.log("compiled")')
                self.assertEqual(package.getmember('package/index.mjs').mode,0o755)

    def test_missing_runtime_artifact_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            (base/'courseflow.module.json').write_text(json.dumps({'runtime':{'entry':'missing','files':[]}}))
            with self.assertRaises(FileNotFoundError): module.pack(base,base/'compiled',{},base)


if __name__=='__main__':unittest.main()
