// Only prototype geometry/count helpers; no model or engineering acceptance.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
const code=html.match(/<script id="domain">([\s\S]*?)<\/script>/)[1];
const ctx={window:{},TextEncoder,DataView,Uint8Array,Uint32Array};vm.runInNewContext(code,ctx);const c=ctx.window.P1Core;
function params(){const p={floorCount:3,desks:24,racks:24,rooms:3};p.rows=c.allocate(p);return p;}
test('L fixture is simple and area is synthetic 480',()=>{assert.equal(c.validatePolygon(c.presets.L),'');assert.equal(c.area(c.presets.L),480);});
test('rectangle fixture area',()=>assert.equal(c.area(c.presets.rectangle),720));
test('self-crossing footprint is rejected',()=>assert.ok(c.validatePolygon([[0,0],[4,4],[0,4],[4,0]])));
test('repeated adjacent vertex rejected',()=>assert.ok(c.validatePolygon([[0,0],[4,0],[4,0],[0,4]])));
test('collinear zero area rejected',()=>assert.ok(c.validatePolygon([[0,0],[1,0],[2,0]])));
test('NaN and oversized coordinates rejected',()=>{assert.ok(c.validatePolygon([[NaN,0],[4,0],[0,4]]));assert.ok(c.validatePolygon([[0,0],[1e6,0],[0,4]]));});
test('absolute straight path decoded',()=>assert.equal(c.area(c.parsePath('M0 0H30V10H10V24H0Z')),440));
test('relative straight path decoded',()=>assert.equal(c.area(c.parsePath('m0 0h30v10h-20v14h-10z')),440));
test('open path rejected',()=>assert.throws(()=>c.parsePath('M0 0L10 0L0 10')));
test('curves explicitly unsupported',()=>assert.throws(()=>c.parsePath('M0 0Q10 10 20 0Z')));
test('multiple subpaths rejected',()=>assert.throws(()=>c.parsePath('M0 0H10V10Z M20 20H30V30Z')));
test('non-divisible cabinet count preserves total',()=>assert.equal(Array.from(c.spread(25,3)).join(','),'9,8,8'));
test('zero division and fractional counts rejected',()=>{assert.throws(()=>c.spread(24,0));assert.throws(()=>c.spread(2.5,3));});
test('default all-building totals consistent',()=>assert.equal(c.validateParams(params()).length,0));
test('25 cabinets split by rooms and floors',()=>{let p=params();p.racks=25;p.rows=c.allocate(p);assert.equal(c.validateParams(p).length,0);assert.equal(p.rows[0].racks,17);});
test('negative and fractional quantities rejected',()=>{let p=params();p.desks=-1;assert.ok(c.validateParams(p).length);p.desks=1.5;assert.ok(c.validateParams(p).length);});
test('empty is not zero',()=>{let p=params();p.racks=null;assert.ok(c.validateParams(p).length);});
test('floor sum mismatch is visible',()=>{let p=params();p.rows[0].desks++;assert.ok(c.validateParams(p).length);});
test('rooms without enough cabinets rejected in this preset',()=>{let p=params();p.rooms=25;assert.ok(c.validateParams(p).length);});
test('one and two floors reallocate without losing totals',()=>{for(const n of [1,2]){let p=params();p.floorCount=n;p.rows=c.allocate(p);assert.equal(c.validateParams(p).length,0);}});
test('SHA-256 matches Node for ASCII unicode and long inputs',()=>{for(const v of ['', 'abc','建筑轮廓','x'.repeat(6000)])assert.equal(c.sha256(v),crypto.createHash('sha256').update(v).digest('hex'));});
test('prototype explicitly prohibits outbound connections',()=>{assert.ok(html.includes("connect-src 'none'"));assert.ok(html.includes('model_execution:false'));assert.ok(html.includes('固定合成三层示意'));});
