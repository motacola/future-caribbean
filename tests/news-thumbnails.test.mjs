import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { publicIPv4, thumbnail, download, main } from '../scripts/news-thumbnails.mjs';
import { mkdtemp, mkdir, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const require = createRequire(import.meta.url);
const sharp = createRequire(require.resolve('astro/package.json'))('sharp');
test('rejects private and metadata addresses', async () => {
  for (const ip of ['127.0.0.2','10.1.1.1','172.20.0.1','192.168.1.1','169.254.169.254','100.64.1.1','0.0.0.0']) assert.equal(publicIPv4(ip),false);
  assert.equal(publicIPv4('8.8.8.8'),true);
  await assert.rejects(download('file:///etc/passwd'));
  await assert.rejects(download('https://127.0.0.1/x'));
});
test('real WebP conversion respects mobile dimensions', async () => {
  const input = await sharp({create:{width:3000,height:1200,channels:3,background:'#ff5500'}}).png().toBuffer();
  const result = await thumbnail(input);
  assert.equal(result.info.format,'webp'); assert.ok(result.info.width<=640); assert.ok(result.info.height<=480);
  assert.ok(result.data.length<input.length);
  await assert.rejects(thumbnail(Buffer.from('not an image')));
});
test('failed downloads retain original data and publish empty manifest', async () => {
  const root=await mkdtemp(join(tmpdir(),'news-thumbnails-'));
  await mkdir(join(root,'data/regional_news'),{recursive:true});
  const payload=JSON.stringify({items:[{image_url:'https://127.0.0.1/nope'}]});
  await writeFile(join(root,'data/regional_news/latest.json'),payload);
  assert.deepEqual(await main(root),{});
  assert.equal(await readFile(join(root,'data/regional_news/latest.json'),'utf8'),payload);
});
