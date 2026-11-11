#!/usr/bin/env python3
"""Exercise the released CLI and HTTP gateway using disposable data only."""
import argparse,hashlib,http.cookiejar,json,os,re,secrets,shutil,socket,subprocess,tarfile,tempfile,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--lock',type=Path,default=root/'.build/images.lock.env');args=p.parse_args()
images=dict(x.split('=',1) for x in args.lock.read_text().splitlines() if x and not x.startswith('#'))
work=Path(tempfile.mkdtemp(prefix='courseflow-smoke-'));state=work/'state'
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
base=f'http://127.0.0.1:{port}';project='courseflow-test-'+secrets.token_hex(4)
config=work/'instance.env';config.write_text(f'PUBLIC_URL={base}\nWEB_PORT={port}\nPROJECT_NAME={project}\nSTATE_DIR={state}\n')
env=dict(os.environ,CF_CONFIG=str(config),CF_IMAGES_LOCK=str(args.lock.resolve()),CF_ALLOW_LOCAL_IMAGES='1')
cli=[str(root/'scripts/courseflow')]
def run(cmd,ok=True,env_override=None):
 result=subprocess.run(cmd,cwd=root,env=env_override or env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if (result.returncode==0)!=ok:raise RuntimeError('Command failed: '+str(cmd)+'\n'+result.stdout)
 return result.stdout
jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));csrf=''
def request(route,method='GET',body=None,status=200,token=None,origin=None,anonymous=False):
 headers={'Origin':origin or base,'Content-Type':'application/json'}
 if method!='GET':headers['x-courseflow-csrf']=csrf if token is None else token
 req=urllib.request.Request(base+route,method=method,headers=headers,data=None if body is None else json.dumps(body).encode())
 try:r=(urllib.request.build_opener() if anonymous else client).open(req,timeout=20)
 except urllib.error.HTTPError as error:r=error
 raw=r.read();assert r.status==status,(route,r.status,status,raw[:200])
 try:data=json.loads(raw)
 except ValueError:data=None
 return data,r.headers,raw
try:
 run(cli+['doctor']);run(cli+['init']);run(cli+['init']);run(cli+['up'])
 assert request('/healthz')[0]['web_api_version']==request('/version.json')[0]['web_api_version']==1
 assert request('/api/bootstrap')[0]['setup_required']
 for route in ['/api/me','/api/admin/users','/api/platforms/sim/courses/a%2Fb/c%2Fd/units']:request(route,status=401,anonymous=True)
 request('/secret.key',status=404)
 code=run(cli+['setup-code']).strip();assert code
 password=secrets.token_urlsafe(24)
 login,headers,_=request('/api/auth/setup','POST',{'setup_code':code,'username':'smoke-admin','password':password})
 csrf=login['csrf'];assert 'HttpOnly' in headers['Set-Cookie'] and 'SameSite=Strict' in headers['Set-Cookie']
 request('/api/auth/logout','POST',{},status=403,token='bad');request('/api/auth/logout','POST',{},status=403,origin='https://wrong.example')
 # Install a synthetic course with opaque IDs through the same package endpoint used by users.
 sim=work/'sim';shutil.copytree(root/'.build/context/framework/modules/simulator',sim)
 entry=sim/'index.mjs';entry.write_text(entry.read_text().replace("'1001'","'1001/encoded'").replace("'9001'","'9001/encoded'"))
 archive=work/'sim.tgz'
 with tarfile.open(archive,'w:gz') as tar:
  for f in sim.iterdir():tar.add(f,arcname=f.name)
 cid=run(['docker','ps','-q','--filter','label=com.docker.compose.project='+project,'--filter','label=com.docker.compose.service=api']).strip()
 run(['docker','exec',cid,'node','--input-type=module','-e',"import dns from 'node:dns/promises'; await dns.lookup('web'); const r=await fetch('https://github.com',{signal:AbortSignal.timeout(20000)}); if(!r.ok)process.exit(1)"])
 run(['docker','cp',str(archive),cid+':/data/sim.tgz'])
 request('/api/modules/install','POST',{'path':'/data/sim.tgz'})
 for mod in ['cx','zhs']:
  request('/api/modules/'+mod+'/config','POST',{'settings':{'source':'fixture',**({'python':'/opt/cx-venv/bin/python'} if mod=='cx' else {})}})
 for mod in ['cx','zhs','sim']:
  begin=request('/api/platforms/'+mod+'/login','POST',{'method':'qr'})[0]['challenge'];challenge=begin.get('id') or begin['session']
  for _ in range(3):
   if request('/api/platforms/'+mod+'/login/'+challenge+'/poll','POST',{})[0]['state']=='connected':break
  else:raise AssertionError('Fixture login did not connect')
  courses=request('/api/platforms/'+mod+'/courses')[0]['courses'];assert courses
  if mod=='sim':
   from urllib.parse import quote
   course=courses[0];assert '/' in course['id']
   assert request('/api/platforms/sim/courses/'+quote(course['id'],safe='')+'/'+quote(course['recruit_id'],safe='')+'/units')[0]['units']
 request('/api/admin/users','POST',{'username':'smoke-member','password':password})
 request('/api/admin/settings','POST',{'max_concurrency':2,'parallel_study':False})
 now=int(time.time());_,headers,body=request(f'/api/logs/export?kind=app&from={now-3600}&to={now+60}');assert body and 'attachment' in headers['Content-Disposition']
 request('/api/auth/logout','POST',{})
 csrf=request('/api/auth/login','POST',{'username':'smoke-member','password':password})[0]['csrf']
 request('/api/admin/users',status=403)
 request('/api/auth/logout','POST',{})
 csrf=request('/api/auth/login','POST',{'username':'smoke-admin','password':password})[0]['csrf']
 run(['docker','cp',str(root/'tests/browser.mjs'),cid+':/tmp/browser.mjs'])
 run(['docker','exec',cid,'node','/tmp/browser.mjs'])
 run(cli+['backup']);before=json.loads((state/'backups/latest/metadata.json').read_text())['data']
 request('/api/admin/users','POST',{'username':'remove-by-restore','password':password})
 run(cli+['restore']);assert len(request('/api/admin/users')[0]['users'])==2
 run(cli+['init']);assert len(request('/api/admin/users')[0]['users'])==2
 run(cli+['update',str(args.lock.resolve())]);assert len(request('/api/admin/users')[0]['users'])==2
 # An invalid web image must restore the working release and paired data.
 bad=work/'bad.env';bad.write_text(f"API_IMAGE={images['API_IMAGE']}\nWEB_IMAGE={images['API_IMAGE']}\n")
 run(cli+['update',str(bad)],ok=False,env_override=dict(env,CF_WAIT_TIMEOUT='20'))
 assert request('/healthz')[0]['status']=='ok';assert len(request('/api/admin/users')[0]['users'])==2
 assert json.loads((state/'backups/latest/metadata.json').read_text())['data']['key_sha256']==before['key_sha256']
 assert sorted(x.name for x in (state/'backups').iterdir())==['latest']
 saved=(state/'backups/latest/data.tar.gz').read_bytes();(state/'backups/latest/data.tar.gz').write_bytes(saved+b'corrupt')
 run(cli+['restore'],ok=False);assert request('/healthz')[0]['status']=='ok'
 (state/'backups/latest/data.tar.gz').write_bytes(saved)
 run(cli+['export-backup',str(work/'offsite')]);assert (work/'offsite/courseflow-backup.tgz').is_file()
 # Fresh recovery directory, original instance stopped to release its public port.
 run(cli+['down']);recovered=work/'recovered';recovery_config=work/'recovery.env'
 recovery_config.write_text(config.read_text().replace(str(state),str(recovered)))
 recovery_env=dict(env,CF_CONFIG=str(recovery_config))
 run(cli+['import-backup',str(work/'offsite/courseflow-backup.tgz')],env_override=recovery_env)
 run(cli+['restore'],env_override=recovery_env)
 assert request('/healthz')[0]['status']=='ok';assert len(request('/api/admin/users')[0]['users'])==2
 run(cli+['down'],env_override=recovery_env)
 print('PASS: initialization, HTTP auth/CSRF/admin, three module contracts, encoded routes, downloads, Chromium sandbox, update failure rollback, corrupt backup rejection and offsite recovery')
finally:
 subprocess.run(cli+['down'],env=env,cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 # All mounts are dedicated synthetic test directories.
 for name in ['state','recovered']:
  target=work/name
  if target.exists():subprocess.run(['docker','run','--rm','--user','0:0','--network','none','-v',str(target)+':/cleanup',images['API_IMAGE'],'sh','-c','rm -rf /cleanup/* /cleanup/.[!.]*'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 shutil.rmtree(work)
