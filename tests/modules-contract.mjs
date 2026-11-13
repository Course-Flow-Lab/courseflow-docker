// 在 --network none 的临时容器中验证实际发布包，绝不读取真实站点数据。
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { createRuntime } from '/app/src/runtime.ts';
import { loadConfig } from '/app/src/core/config.ts';
import { createHttpServer } from '/app/src/server/app.ts';

const catalog=JSON.parse(fs.readFileSync('/packages/catalog.json','utf8'));
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'courseflow-package-check-'));
const runtime=await createRuntime(loadConfig({CF_DATA_DIR:directory,CF_LOG:'error'}),{recoverTasks:false});
const app=createHttpServer(runtime,{bind:'127.0.0.1:0',publicUrl:'http://127.0.0.1:8099',setupCode:'archive-test-code'});
try {
  const setup=await app.inject({method:'POST',url:'/api/auth/setup',payload:{setup_code:'archive-test-code',username:'package-test',password:'offline-package-passphrase-2026'}});
  assert.equal(setup.statusCode,200,setup.body);
  const owner=setup.json().user.id;
  for(const item of catalog.modules){
    const file=path.join('/packages',item.file);
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),item.sha256);
    const listing=execFileSync('tar',['-tzf',file],{encoding:'utf8'}).trim().split('\n');
    assert.ok(listing.includes('package/courseflow.module.json'));
    assert.ok(listing.includes('package/'+item.entry));
    assert.ok(listing.includes('package/LICENSE'));
    assert.ok(listing.every(name=>name.startsWith('package/')&&!name.includes('node_modules/')&&!name.includes('__pycache__/')));
    const row=runtime.manager.install(file);
    assert.equal(row.id,item.id);assert.equal(row.version,item.version);
    runtime.manager.configure(row.id,{source:'fixture',...(row.id==='cx'?{python:'/opt/cx-venv/bin/python'}:{})});
    const descriptor=await runtime.manager.describe(row.id);
    assert.equal(descriptor.module.version,item.version);
    const login=row.id==='unipus'?'password':'qr';
    const challenge=await runtime.manager.loginBegin(owner,row.id,login);
    if(login==='password')await runtime.manager.loginSubmit(owner,row.id,challenge.session,{username:'synthetic',password:'synthetic'});
    let connected=false;
    for(let i=0;i<3;i++)if((await runtime.manager.loginPoll(owner,row.id,challenge.session)).state==='connected'){connected=true;break;}
    assert.ok(connected,'离线登录失败：'+row.id);
    const courses=await runtime.manager.courses(owner,row.id);assert.ok(courses.length);
    const units=await runtime.manager.units(owner,row.id,courses[0]);assert.ok(units.length);
    console.log(`PASS: ${row.id} ${row.version} tgz 安装、握手、离线登录和目录`);
  }
  assert.equal(runtime.db.get('SELECT count(*) AS n FROM write_ledger').n,0);
  execFileSync('/opt/cx-venv/bin/python',['-m','unittest','discover','-s','tests','-v'],{cwd:'/cx-tests',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},stdio:'inherit'});
} finally {
  try {await app.close();}finally{await runtime.close();fs.rmSync(directory,{recursive:true,force:true});}
}
