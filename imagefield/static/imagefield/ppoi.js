;(function() {

  function centerpointWidget() {
    Array.prototype.slice.call(document.querySelectorAll(
      '.imagefield[data-ppoi-id]'
    )).forEach(function(field) {
      var ppoiField = document.querySelector('input[name="' + field.dataset.ppoiId + '"]');
      if (!ppoiField) return;

      var matches = ppoiField.value.match(/^([\.0-9]+)x([\.0-9]+)$/);
      var x, y;
      if (matches) {
        x = parseFloat(matches[1]);
        y = parseFloat(matches[2]);
      } else {
        x = 0.5;
        y = 0.5;
      }

      var point = document.createElement('div'),
        img = field.querySelector('img');
      point.className = 'imagefield-point';
      img.parentNode.appendChild(point);

      point.style.left = (img.clientWidth * x) + 'px';
      point.style.top = (img.clientHeight * y) + 'px';
    });

    document.body.addEventListener('click', function(e) {
      if (e.target && e.target.matches && e.target.matches('img.imagefield-preview-image')) {

        var field = e.target.closest('.imagefield[data-ppoi-id]');
        var ppoiField = document.querySelector('input[name="' + field.dataset.ppoiId + '"]');
        if (!ppoiField) return;

        var point = field.querySelector('.imagefield-point'),
          img = e.target;
        x = e.offsetX / img.clientWidth;
        y = e.offsetY / img.clientHeight;
        ppoiField.value = x.toFixed(2) + 'x' + y.toFixed(2);
        point.style.left = (img.clientWidth * x) + 'px';
        point.style.top = (img.clientHeight * y) + 'px';
      }
    });

  }

  window.addEventListener('load', centerpointWidget);

})();
