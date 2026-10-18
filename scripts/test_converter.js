// 음력 변환기(JS)를 파이썬 엔진 결과와 대조하기 위한 덤프 + 왕복 테스트
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
global.LT = eval(fs.readFileSync(path.join(root, 'assets/js/lunar-table.js'), 'utf8') + ';LT');
const L = require(path.join(root, 'assets/js/converter.js'));
const out = [];
for (let y = 1901; y <= 2049; y++) for (const [m, d] of [[1, 1], [1, 31], [2, 28], [3, 17], [5, 15], [7, 4], [8, 20], [10, 9], [12, 31]]) {
  const r = L.solarToLunar(y, m, d);
  out.push([y, m, d, r.y, r.m, r.d, r.leap ? 1 : 0]);
}
fs.writeFileSync(path.join(root, 'scripts', '_js_out.json'), JSON.stringify(out));
let bad = 0;
for (const o of out) { const s = L.lunarToSolar(o[3], o[4], o[5], !!o[6]); if (!s || s.y !== o[0] || s.m !== o[1] || s.d !== o[2]) bad++; }
console.log('왕복 불일치', bad, '/', out.length);
