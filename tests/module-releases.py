"""离线验证 Release 附件、重试与不可变文件保护，不访问 GitHub。"""
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('module_release',root/'build/publish-module-release.py')
publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)


class ModuleReleaseTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.site=Path(directory.name);(self.site/'modules').mkdir()
        self.file=self.site/'modules/synthetic-1.0.0-node24-abcdef0.tgz';self.file.write_bytes(b'synthetic package')
        self.sha=hashlib.sha256(self.file.read_bytes()).hexdigest()
        checksum=self.sha+'  '+self.file.name+'\n'
        self.file.with_name(self.file.name+'.sha256').write_text(checksum)
        (self.site/'modules/SHA256SUMS').write_text(checksum)
        (self.site/'catalog.json').write_text(json.dumps({'modules':[{'file':'modules/'+self.file.name,'sha256':self.sha,'name':'合成模块','version':'1.0.0','requirements':'Node.js 24+'}]}))
        self.tag,self.assets,self.hashes,_=publisher.release_assets(self.site)
        self.calls=[];self.published=False;self.query_error=None;self.corrupt_download=False

    def run_command(self,args,**kwargs):
        self.calls.append(args)
        if args[:3]==['gh','release','view']:
            if self.query_error:return subprocess.CompletedProcess(args,1,stdout='',stderr=self.query_error)
            if self.published:return subprocess.CompletedProcess(args,0,stdout=json.dumps({'isDraft':False,'assets':[{'name':name} for name in self.hashes]}))
            return subprocess.CompletedProcess(args,1,stdout='',stderr='release not found')
        if args[:3]==['gh','release','download']:
            destination=Path(args[args.index('--dir')+1])
            for file in self.assets:shutil.copyfile(file,destination/file.name)
            if self.corrupt_download:(destination/self.file.name).write_bytes(b'changed')
        return subprocess.CompletedProcess(args,0,stdout='',stderr='')

    def publish(self):return publisher.publish(self.site,'Course-Flow-Lab/courseflow-docker','a'*40,self.run_command)

    def test_create_upload_and_verify_before_publication(self):
        self.assertEqual(self.publish(),self.tag)
        commands=[args[2] for args in self.calls]
        self.assertEqual(commands,['view','create','upload','download','edit'])
        create=self.calls[1];edit=self.calls[-1]
        self.assertIn('--draft',create)
        self.assertIn('--latest=false',create);self.assertIn('--latest=false',edit)
        self.assertIn('--draft=false',edit)
        self.assertEqual({Path(value).name for value in self.calls[2] if Path(value).is_file()},set(self.hashes))

    def test_published_retry_only_verifies_existing_assets(self):
        self.published=True
        self.assertEqual(self.publish(),self.tag)
        self.assertEqual([args[2] for args in self.calls],['view','download'])

    def test_corrupt_published_asset_is_never_overwritten(self):
        self.published=True;self.corrupt_download=True
        with self.assertRaisesRegex(ValueError,'附件与已验收文件不一致'):self.publish()
        self.assertFalse(any(args[2] in ('upload','edit') for args in self.calls))

    def test_local_checksum_failure_prevents_network_and_publication(self):
        self.file.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'校验值不一致'):self.publish()
        self.assertEqual(self.calls,[])

    def test_authorization_failure_is_not_treated_as_missing_release(self):
        self.query_error='HTTP 403: forbidden'
        with self.assertRaisesRegex(RuntimeError,'无法查询'):self.publish()
        self.assertEqual([args[2] for args in self.calls],['view'])

    def test_content_identity_changes_with_catalog_and_blocks_path_escape(self):
        catalog=json.loads((self.site/'catalog.json').read_text())
        catalog['modules'][0]['requirements']='Node.js 25+'
        (self.site/'catalog.json').write_text(json.dumps(catalog))
        self.assertNotEqual(publisher.release_assets(self.site)[0],self.tag)
        catalog['modules'][0]['file']='../private.tgz'
        (self.site/'catalog.json').write_text(json.dumps(catalog))
        with self.assertRaisesRegex(ValueError,'不在发布目录内'):self.publish()


if __name__=='__main__':unittest.main()
