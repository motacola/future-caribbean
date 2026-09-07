// Build-time only: bounded publisher downloads, local WebP, original URL retained.
import { createRequire } from 'node:module';
import { lookup } from 'node:dns/promises';
import https from 'node:https';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const require = createRequire(import.meta.url);
const sharp = createRequire(require.resolve('astro/package.json'))('sharp');
export function publicIPv4(ip) {
  const a = ip.split('.').map(Number);
  return a.length === 4 && a.every(n => Number.isInteger(n) && n >= 0 && n <= 255) &&
    ![0,10,127].includes(a[0]) && a[0] < 224 &&
    !(a[0] === 169 && a[1] === 254) && !(a[0] === 172 && a[1] >= 16 && a[1] <= 31) &&
    !(a[0] === 192 && a[1] === 168) && !(a[0] === 100 && a[1] >= 64 && a[1] <= 127);
}
export async function download(source) {
  const url = new URL(source);
  if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443')) throw Error('Unsafe image URL');
  const addresses = await lookup(url.hostname, { family: 4, all: true });
  if (!addresses.length || addresses.some(a => !publicIPv4(a.address))) throw Error('Non-public image host');
  return new Promise((ok, fail) => {
    const req = https.get(url, { lookup: (_host, options, cb) => options.all ? cb(null, [addresses[0]]) : cb(null, addresses[0].address, 4), headers: {'User-Agent':'Abeng/1.0 news thumbnails'} }, res => {
      if (res.statusCode !== 200) { res.resume(); fail(Error(`HTTP ${res.statusCode}`)); return; }
      let size = 0; const parts = [];
      res.on('data', part => { size += part.length; if (size > 5_000_000) req.destroy(Error('Image exceeds 5MB')); else parts.push(part); });
      res.on('end', () => ok(Buffer.concat(parts)));
      res.on('error', fail);
    });
    const timer = setTimeout(() => req.destroy(Error('Image download timeout')), 12000);
    req.on('close', () => clearTimeout(timer)); req.on('error', fail);
  });
}
export async function thumbnail(bytes) {
  return sharp(bytes, { limitInputPixels: 25_000_000 }).rotate().resize({width:640,height:480,fit:'inside',withoutEnlargement:true}).webp({quality:76}).toBuffer({resolveWithObject:true});
}
export async function main(root = process.cwd()) {
  const payload = JSON.parse(await readFile(resolve(root,'data/regional_news/latest.json'),'utf8'));
  const dir = resolve(root,'public/news-thumbnails'); await mkdir(dir,{recursive:true});
  const sources = [...new Set(payload.items.map(i=>i.image_url || i.imageUrl).filter(Boolean))].slice(0,32);
  const manifest = {}; let cursor = 0; let failed = 0;
  await Promise.all(Array.from({length:3}, async () => {
    while (cursor < sources.length) {
      const source = sources[cursor++];
      const name = createHash('sha256').update('640x480-q76-v1:'+source).digest('hex')+'.webp';
      try {
        let data, info;
        try { data = await readFile(resolve(dir,name)); info = await sharp(data).metadata(); }
        catch { ({data,info} = await thumbnail(await download(source))); await writeFile(resolve(dir,name),data); }
        manifest[source] = {url:'/news-thumbnails/'+name,width:info.width,height:info.height,bytes:data.length};
      } catch(e) { failed++; console.warn('thumbnail fallback:', new URL(source).hostname, e.message); }
    }
  }));
  await writeFile(resolve(dir,'index.json'),JSON.stringify(manifest,null,2)+'\n');
  console.log(JSON.stringify({thumbnails:Object.keys(manifest).length,failed,bytes:Object.values(manifest).reduce((n,x)=>n+x.bytes,0)}));
  return manifest;
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) await main();
