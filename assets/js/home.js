/* 홈: 오늘 날짜 위젯 + 다가오는 공휴일/손 없는 날 (CAL 은 caldata.js) */
(function () {
  var C = window.CAL;
  if (!C) return;
  var STEMS = '갑을병정무기경신임계', BR = '자축인묘진사오미신유술해';
  var ANI = ['쥐', '소', '호랑이', '토끼', '용', '뱀', '말', '양', '원숭이', '닭', '개', '돼지'];
  var WD = ['일', '월', '화', '수', '목', '금', '토'];
  var sp = C.s.split('-');
  var T0 = Date.UTC(+sp[0], +sp[1] - 1, +sp[2]);
  function two(n) { return (n < 10 ? '0' : '') + n; }
  function dateOf(i) { var d = new Date(T0 + i * 864e5); return d; }
  function iso(i) { var d = dateOf(i); return d.getUTCFullYear() + '-' + two(d.getUTCMonth() + 1) + '-' + two(d.getUTCDate()); }
  function label(i) { var d = dateOf(i); return (d.getUTCMonth() + 1) + '월 ' + d.getUTCDate() + '일(' + WD[d.getUTCDay()] + ')'; }
  var now = new Date();
  var ti = Math.round((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - T0) / 864e5);
  var n = C.d.length;
  var box = document.getElementById('today-box');
  if (!box) return;
  if (ti < 0 || ti >= n) { ti = 0; }
  function isSon(e) { var r = e[1] % 10; return r === 9 || r === 0; }
  var e = C.d[ti];
  var lm = e[0] % 100, leap = e[0] >= 100;
  var gi = e[2];
  var nextHol = -1, nextSon = -1;
  for (var k = ti + 1; k < n; k++) {
    if (nextHol < 0 && C.d[k][5] >= 0) nextHol = k;
    if (nextSon < 0 && isSon(C.d[k])) nextSon = k;
    if (nextHol >= 0 && nextSon >= 0) break;
  }
  function dd(k) { return k - ti === 0 ? '오늘' : (k - ti) + '일 뒤'; }
  var cells = [
    ['오늘 (양력)', label(ti)],
    ['음력', (leap ? '윤' : '') + lm + '월 ' + e[1] + '일'],
    ['일진', STEMS[gi % 10] + BR[gi % 12] + '일 · ' + ANI[gi % 12] + '의 날'],
    ['손 없는 날', isSon(e) ? '예 (오늘!)' : '아니요'],
    ['다음 공휴일', nextHol >= 0 ? C.h[C.d[nextHol][5]] + ' · ' + dd(nextHol) : '-'],
    ['다음 손 없는 날', nextSon >= 0 ? label(nextSon) + ' · ' + dd(nextSon) : '-']
  ];
  box.innerHTML = cells.map(function (c) { return '<div><small>' + c[0] + '</small><b>' + c[1] + '</b></div>'; }).join('');
  var line = document.getElementById('today-line');
  if (line) line.innerHTML = '<a href="/date/' + iso(ti) + '/" style="color:#fff;text-decoration:underline">' + label(ti) + ' 상세 보기 →</a> · 이사·결혼·개업 길일 판정까지';
  var up = document.getElementById('upcoming');
  if (!up) return;
  var hs = [], ss = [];
  for (var j = ti; j < n && (hs.length < 6 || ss.length < 6); j++) {
    if (C.d[j][5] >= 0 && hs.length < 6) hs.push(j);
    if (isSon(C.d[j]) && ss.length < 6) ss.push(j);
  }
  function card(j, t, sub) { return '<a class="card" href="/date/' + iso(j) + '/"><b>' + t + '</b><span>' + sub + '</span></a>'; }
  up.innerHTML = '<h2 class="group-title">⏳ 다가오는 공휴일</h2><div class="card-grid">' + hs.map(function (j) { return card(j, label(j), C.h[C.d[j][5]] + ' · ' + dd(j)); }).join('') + '</div>' +
    '<h2 class="group-title">🧭 다가오는 손 없는 날</h2><div class="card-grid">' + ss.map(function (j) { var q = C.d[j]; return card(j, label(j), '음력 ' + (q[0] % 100) + '월 ' + q[1] + '일 · ' + dd(j)); }).join('') + '</div>';
})();
