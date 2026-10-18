/* 음력 ↔ 양력 변환기 (LT 는 lunar-table.js: [음력연, 설날의 1900-01-01 기준 일수, 윤달월, 월별 대소]) */
var LunarConv = (function () {
  var EPOCH = Date.UTC(1900, 0, 1);
  var STEMS = '갑을병정무기경신임계', BR = '자축인묘진사오미신유술해';
  var ANI = ['쥐', '소', '호랑이', '토끼', '용', '뱀', '말', '양', '원숭이', '닭', '개', '돼지'];
  var WD = ['일', '월', '화', '수', '목', '금', '토'];
  function dayNum(y, m, d) { return Math.round((Date.UTC(y, m - 1, d) - EPOCH) / 864e5); }
  function gz(i) { return STEMS[i % 10] + BR[i % 12]; }
  function ganjiOfDay(n) { return (693596 + n + 14) % 60; }
  function solarToLunar(y, m, d) {
    var n = dayNum(y, m, d), k = -1;
    for (var i = 0; i < LT.length; i++) { if (LT[i][1] <= n) k = i; else break; }
    if (k < 0) return null;
    var e = LT[k], off = n - e[1], bits = e[3], leap = e[2], mi;
    for (mi = 0; mi < bits.length; mi++) {
      var len = bits.charAt(mi) === '1' ? 30 : 29;
      if (off < len) break;
      off -= len;
    }
    if (mi >= bits.length) return null;
    var month, isLeap = false;
    if (!leap || mi < leap) month = mi + 1;
    else if (mi === leap) { month = leap; isLeap = true; }
    else month = mi;
    return { y: e[0], m: month, d: off + 1, leap: isLeap, n: n };
  }
  function lunarToSolar(y, m, d, leap) {
    var e = null;
    for (var i = 0; i < LT.length; i++) if (LT[i][0] === y) { e = LT[i]; break; }
    if (!e) return null;
    var lm = e[2], bits = e[3], idx;
    if (leap) { if (lm !== m) return null; idx = m; }
    else idx = (lm && m > lm) ? m : m - 1;
    if (idx >= bits.length) return null;
    var len = bits.charAt(idx) === '1' ? 30 : 29;
    if (d < 1 || d > len) return null;
    var n = e[1];
    for (var j = 0; j < idx; j++) n += bits.charAt(j) === '1' ? 30 : 29;
    n += d - 1;
    var dt = new Date(EPOCH + n * 864e5);
    return { y: dt.getUTCFullYear(), m: dt.getUTCMonth() + 1, d: dt.getUTCDate(), n: n };
  }
  function describe(n, lunar, solar) {
    var dt = new Date(EPOCH + n * 864e5);
    var g = ganjiOfDay(n);
    var yi = (lunar.y - 4) % 60;
    var son = (lunar.d % 10 === 9 || lunar.d % 10 === 0);
    return { solar: solar, lunar: lunar, wd: WD[dt.getUTCDay()], gz: gz(g), animal: ANI[g % 12], year: gz(yi), yAnimal: ANI[yi % 12], son: son };
  }
  return { solarToLunar: solarToLunar, lunarToSolar: lunarToSolar, describe: describe, dayNum: dayNum };
})();

(function () {
  if (typeof document === 'undefined' || !document.getElementById('s-go')) return;
  function two(n) { return (n < 10 ? '0' : '') + n; }
  function pageLink(y, m, d) { return '/date/' + y + '-' + two(m) + '-' + two(d) + '/'; }
  function show(el, r) {
    var s = r.solar, l = r.lunar;
    var inRange = s.y >= 2026 && s.y <= 2030;
    el.innerHTML = '<b>양력 ' + s.y + '년 ' + s.m + '월 ' + s.d + '일(' + r.wd + ')</b><br>' +
      '<b>음력 ' + l.y + '년 ' + (l.leap ? '윤' : '') + l.m + '월 ' + l.d + '일</b> · ' + r.year + '년(' + r.yAnimal + '띠)<br>' +
      '일진 ' + r.gz + '일(' + r.animal + '의 날) · ' + (r.son ? '손 없는 날입니다' : '손 없는 날은 아닙니다') +
      (inRange ? '<br><a href="' + pageLink(s.y, s.m, s.d) + '">이 날짜의 이사·결혼·개업 길일 판정 보기 →</a>' : '');
  }
  document.getElementById('s-go').onclick = function () {
    var y = +document.getElementById('s-y').value, m = +document.getElementById('s-m').value, d = +document.getElementById('s-d').value;
    var out = document.getElementById('s-out');
    var dt = new Date(Date.UTC(y, m - 1, d));
    if (dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) { out.textContent = '존재하지 않는 양력 날짜입니다.'; return; }
    var l = LunarConv.solarToLunar(y, m, d);
    if (!l) { out.textContent = '1900년 1월 31일 ~ 2050년 사이의 날짜만 변환할 수 있습니다.'; return; }
    show(out, LunarConv.describe(l.n, l, { y: y, m: m, d: d }));
  };
  document.getElementById('l-go').onclick = function () {
    var y = +document.getElementById('l-y').value, m = +document.getElementById('l-m').value, d = +document.getElementById('l-d').value;
    var leap = document.getElementById('l-leap').checked;
    var out = document.getElementById('l-out');
    var s = LunarConv.lunarToSolar(y, m, d, leap);
    if (!s) { out.textContent = leap ? '그 해에 해당 윤달이 없거나 날짜가 올바르지 않습니다.' : '올바르지 않은 음력 날짜입니다(그 달은 29일까지일 수 있습니다).'; return; }
    show(out, LunarConv.describe(s.n, { y: y, m: m, d: d, leap: leap }, s));
  };
})();
if (typeof module !== 'undefined') module.exports = LunarConv;
