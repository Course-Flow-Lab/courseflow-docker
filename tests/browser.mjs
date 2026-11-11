import fs from 'node:fs';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
assert.notEqual(process.getuid(),0);
const profile=fs.mkdtempSync('/tmp/courseflow-chromium-check-');
const child=spawn('/usr/bin/chromium',['--headless=new','--disable-dev-shm-usage','--no-first-run','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:['ignore','ignore','pipe']});
let stderr=''; child.stderr.on('data',c=>stderr=(stderr+String(c)).slice(-12000));
let socket;
try {
 const socketUrl=await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(new Error('Chromium CDP timeout: '+stderr)),25000);
  child.once('error',e=>{clearTimeout(timer);reject(e)});
  child.once('exit',code=>{clearTimeout(timer);reject(new Error('Chromium exited '+code+': '+stderr))});
  child.stderr.on('data',()=>{const m=/DevTools listening on (ws:\/\/127\.0\.0\.1:\d+\/devtools\/browser\/[\w-]+)/.exec(stderr);if(m){clearTimeout(timer);resolve(m[1]);}});
 });
 socket=new WebSocket(socketUrl);
 await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
 let id=0; const pending=new Map();
 socket.addEventListener('message',e=>{const r=JSON.parse(String(e.data));if(pending.has(r.id)){const {resolve,reject}=pending.get(r.id);pending.delete(r.id);r.error?reject(new Error(JSON.stringify(r.error))):resolve(r.result)}});
 const call=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params,...(sessionId?{sessionId}:{})}));});
 const {targetId}=await call('Target.createTarget',{url:'chrome://sandbox'});
 const {sessionId}=await call('Target.attachToTarget',{targetId,flatten:true});
 let text='';
 for(let i=0;i<30;i++){
  const r=await call('Runtime.evaluate',{expression:'document.body.innerText',returnByValue:true},sessionId);
  text=r.result.value||'';
  if(/Seccomp|sandboxed/.test(text))break;
  await new Promise(r=>setTimeout(r,100));
 }
 assert.match(text,/Seccomp-BPF sandbox\s+Yes/);
 assert.match(text,/PID namespaces\s+Yes/);
 assert.ok(!fs.readFileSync(`/proc/${child.pid}/cmdline`,'utf8').includes('--no-sandbox'));
 console.log(JSON.stringify({uid:process.getuid(),sandbox:text.trim(),cdp:'container loopback',passed:true}));
} finally {
 socket?.close();
 const ended=new Promise(resolve=>child.once('exit',resolve));
 if(child.exitCode===null){child.kill('SIGTERM');await Promise.race([ended,new Promise(r=>setTimeout(r,5000))]);if(child.exitCode===null)child.kill('SIGKILL');}
 fs.rmSync(profile,{recursive:true,force:true});
}
