// Exercise the deployed host-to-captcha HTTP path with a generated transparent patch.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {CaptchaService} from '/app/src/services/captcha.ts';

const payload=JSON.parse(execFileSync('/opt/captcha-venv/bin/python',['-c',`
import base64,io,json,random
from PIL import Image
rng=random.Random(172)
background=Image.frombytes('RGB',(240,100),rng.randbytes(240*100*3))
piece=Image.new('RGBA',(36,38))
piece.paste(background.crop((123,41,153,73)),(3,4))
def encoded(image):
    out=io.BytesIO();image.save(out,format='PNG')
    return base64.b64encode(out.getvalue()).decode()
print(json.dumps({'target_image':encoded(piece),'background_image':encoded(background)}))
`],{encoding:'utf8'}));
const service=new CaptchaService({url:process.env.CF_CAPTCHA_URL});
try {
  const result=await service.recognize('slide_match',payload);
  assert.ok(Math.abs(result.target[0]-result.target_x-120)<=1);
  console.log('PASS: API connects to the internal captcha service and matches a synthetic transparent patch');
} finally {await service.shutdown();}
