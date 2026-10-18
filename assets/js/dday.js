/* [data-date] 요소에 오늘 기준 D-day 표시 */
(function () {
  var els = document.querySelectorAll('[data-date]');
  var now = new Date();
  var t = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  for (var i = 0; i < els.length; i++) {
    var p = els[i].getAttribute('data-date').split('-');
    var diff = Math.round((Date.UTC(+p[0], +p[1] - 1, +p[2]) - t) / 864e5);
    els[i].textContent = diff > 0 ? 'D-' + diff : diff === 0 ? 'D-day' : Math.abs(diff) + '일 지남';
  }
})();
