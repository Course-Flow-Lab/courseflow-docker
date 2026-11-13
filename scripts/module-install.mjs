// 在停止服务后的临时 API 容器内运行；stdin 为本地 tgz，不需要修改宿主文件权限。
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRuntime } from '/app/src/runtime.ts';
import { loadConfig } from '/app/src/core/config.ts';

const directory=fs.mkdtempSync(path.join(os.tmpdir(),'courseflow-module-'));
let runtime;
try {
  const chunks=[];let size=0;
  for await(const chunk of process.stdin){size+=chunk.length;if(size>64*1024*1024)throw Error('模块安装包不能超过 64 MiB');chunks.push(chunk);}
  const file=path.join(directory,'module.tgz');fs.writeFileSync(file,Buffer.concat(chunks),{mode:0o600});
  runtime=await createRuntime(loadConfig(),{recoverTasks:false,logLevel:'error'});
  const row=runtime.manager.install(file);
  await runtime.manager.describe(row.id);
  console.log(`已安装并验证模块 ${row.id} ${row.version}`);
} finally {
  try {await runtime?.close();}finally{fs.rmSync(directory,{recursive:true,force:true});}
}
