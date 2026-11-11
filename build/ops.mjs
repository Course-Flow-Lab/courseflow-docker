// Runs inside the API image; no host Node/Python dependency.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {DatabaseSync} from 'node:sqlite';
import assert from 'node:assert/strict';
const [cmd,...args]=process.argv.slice(2),state='/state',data='/state/data';
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const mkdir=p=>fs.mkdirSync(p,{recursive:true,mode:0o700});
function files(dir,prefix='') {return fs.readdirSync(dir,{withFileTypes:true}).flatMap(x=>x.isDirectory()?files(path.join(dir,x.name),prefix+x.name+'/'):[prefix+x.name]);}
function own(dir) {for(const f of ['',...files(dir)])fs.chownSync(path.join(dir,f),Number(process.env.CF_HOST_UID),Number(process.env.CF_HOST_GID));const walk=p=>{fs.chownSync(p,Number(process.env.CF_HOST_UID),Number(process.env.CF_HOST_GID));for(const e of fs.readdirSync(p,{withFileTypes:true}))if(e.isDirectory())walk(path.join(p,e.name));};walk(dir);}
function inspect(dir) {
 const key=fs.readFileSync(path.join(dir,'secret.key'));assert.equal(key.length,32,'Expected original 32-byte master key');
 const db=new DatabaseSync(path.join(dir,'courseflow.db'),{readOnly:true});
 try {assert.equal(db.prepare('PRAGMA quick_check').get().quick_check,'ok');
  for(const m of db.prepare('SELECT path FROM modules').all()) {assert.ok(m.path.startsWith('/data/modules/'));assert.ok(fs.existsSync(path.join(dir,m.path.slice('/data/'.length),'courseflow.module.json')));}
  return {key_sha256:sha(path.join(dir,'secret.key')),schema:db.prepare('PRAGMA user_version').get().user_version,users:db.prepare('SELECT count(*) AS n FROM users').get().n,tasks:db.prepare('SELECT count(*) AS n FROM tasks').get().n};
 } finally {db.close();}
}
function verify(dir) {
 for(const line of fs.readFileSync(path.join(dir,'SHA256SUMS'),'utf8').trim().split('\n')) {
  const [hash,file]=line.split('  ');assert.ok(file && !path.isAbsolute(file) && !file.split('/').includes('..'));assert.equal(sha(path.join(dir,file)),hash,'Backup checksum mismatch: '+file);
 }
 const tmp=fs.mkdtempSync('/tmp/courseflow-verify-');
 try {
  execFileSync('tar',['-xzf',path.join(dir,'data.tar.gz'),'-C',tmp]);
  const info=inspect(tmp);assert.deepEqual(info,read(path.join(dir,'metadata.json')).data);return info;
 } finally {fs.rmSync(tmp,{recursive:true,force:true});}
}
async function modules(update=false) {
 const base='/data',marker=path.join(base,'.initialized'),partial=path.join(base,'.initializing');
 if(!update && fs.existsSync(marker)) {inspect(base);console.log('Existing instance verified; initialization is unchanged');return;}
 if(!update && !fs.existsSync(partial)) {assert.equal(fs.readdirSync(base).length,0,'Existing unrecognized data directory; refusing to initialize');fs.writeFileSync(partial,'1',{mode:0o600});}
 const {createRuntime}=await import('/app/src/runtime.ts'),{loadConfig}=await import('/app/src/core/config.ts');
 const lock=read('/opt/courseflow-tools/sources.lock.json');
 const installed=fs.existsSync(path.join(base,'.components.json'))?read(path.join(base,'.components.json')):{};
 const r=await createRuntime(loadConfig(),{recoverTasks:false,logLevel:'error'});
 try {
  for(const [id,key] of [['zhs','zhs'],['cx','cx']]) {
   const old=r.db.get('SELECT settings FROM modules WHERE id=?1',id);
   if(old && installed[id]===lock.components[key].commit)continue;
   r.manager.install('/opt/courseflow-modules/'+id);
   if(!old)r.manager.configure(id,{source:'live',...(id==='cx'?{python:'/opt/cx-venv/bin/python'}:{})});
   installed[id]=lock.components[key].commit;
  }
 } finally {await r.close();}
 fs.writeFileSync(path.join(base,'.components.json'),JSON.stringify(installed),{mode:0o600});
 fs.writeFileSync(marker,'1',{mode:0o600});fs.rmSync(partial,{force:true});console.log('Live platform modules initialized');
}
if(cmd==='prepare') {mkdir(data);fs.chownSync(data,1000,1000);fs.chmodSync(data,0o700);}
else if(cmd==='init'||cmd==='upgrade-modules')await modules(cmd==='upgrade-modules');
else if(cmd==='inspect')console.log(JSON.stringify(inspect(data)));
else if(cmd==='backup') {
 const backups=state+'/backups';mkdir(backups);fs.chownSync(backups,Number(process.env.CF_HOST_UID),Number(process.env.CF_HOST_GID));const tmp=fs.mkdtempSync(backups+'/.new-');
 try {
  execFileSync('tar',['--exclude=./browser-runtime','-czf',tmp+'/data.tar.gz','-C',data,'.']);
  fs.cpSync(state+'/deployment',tmp+'/deployment',{recursive:true});
  fs.writeFileSync(tmp+'/metadata.json',JSON.stringify({created_at:new Date().toISOString(),data:inspect(data)},null,2)+'\n',{mode:0o600});
  fs.writeFileSync(tmp+'/SHA256SUMS',files(tmp).sort().map(f=>sha(tmp+'/'+f)+'  '+f+'\n').join(''),{mode:0o600});
  verify(tmp);own(tmp);
  // Keep the old snapshot until the new archive has passed extraction and SQLite checks.
  const latest=backups+'/latest',old=backups+'/.previous';
  if(fs.existsSync(old)) {if(!fs.existsSync(latest))fs.renameSync(old,latest);else fs.rmSync(old,{recursive:true});}
  if(fs.existsSync(latest))fs.renameSync(latest,old);
  fs.renameSync(tmp,latest);fs.rmSync(old,{recursive:true,force:true});
  console.log('One verified backup retained: backups/latest');
 } finally {fs.rmSync(tmp,{recursive:true,force:true});}
}
else if(cmd==='verify-backup')console.log(JSON.stringify(verify(state+'/backups/latest')));
else if(cmd==='restore') {
 const backup=state+'/backups/latest';verify(backup);
 const temp=state+'/.restore-data';assert.ok(!fs.existsSync(temp),'Unfinished restore; inspect .restore-data');mkdir(temp);
 execFileSync('tar',['-xzf',backup+'/data.tar.gz','-C',temp]);inspect(temp);
 const failed=state+'/.failed-data';assert.ok(!fs.existsSync(failed),'Unresolved failed restore; inspect .failed-data');
 if(fs.existsSync(data))fs.renameSync(data,failed);
 fs.renameSync(temp,data);
 fs.rmSync(state+'/deployment',{recursive:true,force:true});fs.cpSync(backup+'/deployment',state+'/deployment',{recursive:true});own(state+'/deployment');
 console.log('Matching database, key, modules and deployment restored');
}
else if(cmd==='finish-restore')fs.rmSync(state+'/.failed-data',{recursive:true,force:true});
else if(cmd==='export') {
 verify(state+'/backups/latest');const tmp='/export/.courseflow-backup.tmp';
 execFileSync('tar',['-czf',tmp,'-C',state+'/backups/latest','.']);
 fs.chmodSync(tmp,0o600);fs.chownSync(tmp,Number(process.env.CF_HOST_UID),Number(process.env.CF_HOST_GID));
 fs.renameSync(tmp,'/export/courseflow-backup.tgz');console.log('Verified backup exported to courseflow-backup.tgz');
}
else if(cmd==='import') {
 const dest=state+'/backups';mkdir(dest);fs.chownSync(dest,Number(process.env.CF_HOST_UID),Number(process.env.CF_HOST_GID));assert.ok(!fs.existsSync(dest+'/latest'),'Existing backup present; import only into a new recovery instance');
 const tmp=fs.mkdtempSync(dest+'/.import-');
 try {execFileSync('tar',['-xzf','/import/backup.tgz','-C',tmp]);verify(tmp);own(tmp);fs.renameSync(tmp,dest+'/latest');}
 finally {fs.rmSync(tmp,{recursive:true,force:true});}
}
else throw Error('Unknown maintenance operation: '+cmd);
