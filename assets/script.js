/**
 * 涮涮AI - 抽屉升降动画（四大支柱之一：JS 仅负责视觉）
 * 实际通过 Gradio head= 注入的是 ui.py 中的 _HEAD_JS 内联脚本；
 * 本文件为独立参考，便于与样式分离维护。
 */
(function () {
  function safeFind(selector) {
    var el = document.querySelector(selector);
    if (el) return el;
    var frames = document.querySelectorAll('iframe');
    for (var i = 0; i < frames.length; i++) {
      try {
        var d = frames[i].contentDocument || frames[i].contentWindow.document;
        el = d.querySelector(selector);
        if (el) return el;
      } catch (e) {}
    }
    return null;
  }

  window.shuaiToggleDrawer = function (show) {
    var overlay = safeFind('#shuai-global-overlay');
    var drawer = safeFind('#drawer-fixed-container');
    if (!overlay || !drawer) return;
    if (show) {
      overlay.style.display = 'block';
      setTimeout(function () {
        overlay.classList.add('active');
        drawer.classList.add('active');
      }, 10);
    } else {
      overlay.classList.remove('active');
      drawer.classList.remove('active');
      setTimeout(function () {
        overlay.style.display = 'none';
      }, 300);
    }
  };
})();
