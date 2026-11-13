#!/usr/bin/env python3
"""离线验证 latest 发布、降级保护及远端更新入口。"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('promote_latest', root/'build/promote-latest.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
registry = 'ghcr.io/course-flow-lab'


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.releases = [{'tagName': 'v0.1.2', 'isDraft': False, 'isPrerelease': False},
                         {'tagName': 'v0.1.4', 'isDraft': True, 'isPrerelease': False},
                         {'tagName': 'v0.2.0', 'isDraft': False, 'isPrerelease': True}]
        self.manifest = {'version': 'v0.1.3', 'images': {}}
        self.images = {}
        for service, name, ident in [('api','api','a'), ('web','webui','b')]:
            tag = registry+'/courseflow-'+name+':v0.1.3'
            digest = registry+'/courseflow-'+name+'@sha256:'+ident*64
            self.manifest['images'][service] = {'tag': tag, 'digest': digest, 'id': 'sha256:'+ident*64}
            self.images[tag] = {'Id': 'sha256:'+ident*64, 'RepoDigests': [digest],
                'Config': {'Labels': {'org.opencontainers.image.version': 'v0.1.3'}}}

    def run_command(self, args, **kwargs):
        self.calls.append(args)
        if args[:3] == ['gh','release','list']: body = self.releases
        elif args[:3] == ['docker','image','inspect']: body = [self.images[args[-1]]]
        else: body = None
        return subprocess.CompletedProcess(args,0,stdout=json.dumps(body))

    def promote(self):
        return publisher.promote('v0.1.3', self.manifest, 'Course-Flow-Lab/courseflow-docker', self.run_command)

    def test_both_latest_tags_use_verified_version_images(self):
        self.assertTrue(self.promote())
        tags = [args for args in self.calls if args[:2] == ['docker','tag']]
        pushes = [args[-1] for args in self.calls if args[:2] == ['docker','push']]
        self.assertEqual(tags, [['docker','tag',registry+'/courseflow-'+name+':v0.1.3',registry+'/courseflow-'+name+':latest'] for name in ['api','webui']])
        self.assertEqual(pushes, [registry+'/courseflow-api:latest',registry+'/courseflow-webui:latest'])

    def test_older_release_cannot_replace_newer_latest(self):
        self.releases.append({'tagName':'v0.1.10','isDraft':False,'isPrerelease':False})
        self.assertFalse(self.promote())
        self.assertFalse(any(args[0]=='docker' for args in self.calls))

    def test_verify_both_images_before_changing_any_tags(self):
        self.images[registry+'/courseflow-webui:v0.1.3']['Config']['Labels']['org.opencontainers.image.version'] = 'v0.1.2'
        with self.assertRaisesRegex(ValueError,'清单不一致'): self.promote()
        self.assertFalse(any(args[1] in ('tag','push') for args in self.calls))

    def test_wrong_digest_or_manifest_version_stops_promotion(self):
        self.manifest['images']['web']['digest'] = 'sha256:wrong'
        with self.assertRaises(ValueError): self.promote()
        self.assertFalse(any(args[1] in ('tag','push') for args in self.calls))
        self.manifest['version'] = 'v0.1.2'
        with self.assertRaises(ValueError): self.promote()


DOCKER = '''#!/usr/bin/env python3
import json,os,sys
args=sys.argv[1:]
with open(os.environ['SYNTHETIC_LOG'],'a') as log: log.write(json.dumps(args)+'\\n')
scenario=os.environ['SYNTHETIC_SCENARIO']
if args[0]=='pull':
    if scenario=='pull-failure' and 'webui' in args[-1]: sys.exit(2)
elif args[:2]==['image','inspect'] and args[-1].endswith(':latest'):
    web='webui' in args[-1]
    if 'Labels' in args[3]:
        print('dev' if scenario=='bad-version' else 'v0.1.2' if web and scenario=='mixed' else 'v0.1.3')
    else:
        print('unrelated.example/image@sha256:'+'f'*64)
        if scenario!='missing-digest': print(args[-1].removesuffix(':latest')+'@sha256:'+('b' if web else 'a')*64)
elif args[0]=='compose' and 'ps' in args: print('synthetic-'+args[-1])
elif args[0]=='inspect': print('healthy')
elif args[0] not in ('image','run','compose'): sys.exit(2)
'''


class UpdateTests(unittest.TestCase):
    def exercise(self, scenario):
        with tempfile.TemporaryDirectory(prefix='courseflow-latest-') as name:
            tmp = Path(name)
            binary = tmp/'bin'; binary.mkdir()
            docker = binary/'docker'; docker.write_text(DOCKER); docker.chmod(0o755)
            state = tmp/'state'; deployment = state/'deployment'; deployment.mkdir(parents=True)
            previous = f'API_IMAGE={registry}/courseflow-api@sha256:'+('c'*64)+f'\nWEB_IMAGE={registry}/courseflow-webui@sha256:'+('d'*64)+'\n'
            (deployment/'images.lock.env').write_text(previous)
            config = tmp/'instance.env'; config.write_text(f'PUBLIC_URL=http://127.0.0.1:8100\nSTATE_DIR={state}\n')
            log = tmp/'docker.jsonl'
            env = {**os.environ,'PATH':str(binary)+':'+os.environ['PATH'],'CF_CONFIG':str(config),
                   'SYNTHETIC_LOG':str(log),'SYNTHETIC_SCENARIO':scenario}
            result = subprocess.run([str(root/'scripts/courseflow'),'update','latest'],env=env,text=True,capture_output=True)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            pulls = [args[-1] for args in calls if args[0]=='pull']
            self.assertEqual(pulls,[registry+'/courseflow-api:latest',registry+'/courseflow-webui:latest'] if scenario not in ('bad-version','missing-digest') else [registry+'/courseflow-api:latest'])
            if scenario=='ok':
                self.assertEqual(result.returncode,0,result.stderr)
                expected = f'API_IMAGE={registry}/courseflow-api@sha256:'+('a'*64)+f'\nWEB_IMAGE={registry}/courseflow-webui@sha256:'+('b'*64)+'\n'
                self.assertEqual((state/'images.latest.env').read_text(),expected)
                self.assertEqual((deployment/'images.lock.env').read_text(),expected)
                self.assertTrue(any(args[0]=='run' and 'backup' in args for args in calls))
                self.assertTrue(any(args[0]=='compose' and '--wait' in args for args in calls))
            else:
                self.assertNotEqual(result.returncode,0)
                self.assertEqual((deployment/'images.lock.env').read_text(),previous)
                self.assertFalse((state/'images.latest.env').exists())
                self.assertFalse(any(args[0] in ('compose','run') for args in calls),'拉取与配对失败不能停止现有服务或写入备份')

    def test_always_pull_latest_then_deploy_pinned_digests(self): self.exercise('ok')
    def test_reject_mixed_versions_before_stopping_services(self): self.exercise('mixed')
    def test_pull_failure_keeps_current_deployment(self): self.exercise('pull-failure')
    def test_reject_nonrelease_labels(self): self.exercise('bad-version')
    def test_reject_missing_digest(self): self.exercise('missing-digest')


if __name__=='__main__': unittest.main()
