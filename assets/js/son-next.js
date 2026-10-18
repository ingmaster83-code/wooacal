/* 손 없는 날 허브: 다음 손 없는 날 5개 */
(function () {
  var C = window.CAL, box = document.getElementById('son-next');
  if (!C || !box) return;
  var WD = ['일', '월', '화', '수', '목', '금', '토'];
  var sp = C.s.split('-'), T0 = Date.UTC(+sp[0], +sp[1] - 1, +sp[2]);
  var now = new Date();
  var ti = Math.round((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - T0) / 864e5);
  if (ti < 0) ti = 0;
  var out = [];
  for (var k = ti; k < C.d.length && out.length < 5; k++) {
    var r = C.d[k][1] % 10;
    if (r === 9 || r === 0) {
      var d = new Date(T0 + k * 864e5);
      out.push('<div><small>' + (k === ti ? '오늘' : (k - ti) + '일 뒤') + '</small><b>' + (d.getUTCMonth() + 1) + '월 ' + d.getUTCDate() + '일(' + WD[d.getUTCDay()] + ')</b></div>');
    }
  }
  box.innerHTML = out.join('') || '';
  if (!out.length) box.style.display = 'none';
})();
