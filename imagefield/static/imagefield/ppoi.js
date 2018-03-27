;(function() {

  function centerpointWidget() {
    function movePoint(point, img, x, y) {
      point.style.left = (img.clientWidth * x) + 'px';
      point.style.top = (img.clientHeight * y) + 'px';
    }

    Array.prototype.slice.call(document.querySelectorAll(
      '.imagefield[data-ppoi-id]'
    )).forEach(function(field) {
      if (!field.dataset.ppoiId) return;
      var ppoiField = document.querySelector('#' + field.dataset.ppoiId);
      if (!ppoiField) return;

      var point = document.createElement('div'),
        img = field.querySelector('img');
      point.className = 'imagefield-point opaque';
      img.parentNode.appendChild(point);

      setTimeout(function() { point.className = 'imagefield-point'; }, 1000);

      var matches = ppoiField.value.match(/^([\.0-9]+)x([\.0-9]+)$/);
      var x, y;
      if (matches) {
        movePoint(point, img, parseFloat(matches[1]), parseFloat(matches[2]));
      } else {
        movePoint(point, img, .5, .5);
      }

      point.style.left = (img.clientWidth * x) + 'px';
      point.style.top = (img.clientHeight * y) + 'px';
    });

    document.body.addEventListener('click', function(e) {
      if (e.target && e.target.matches && e.target.matches('img.imagefield-preview-image')) {

        var field = e.target.closest('.imagefield[data-ppoi-id]');
        if (!field.dataset.ppoiId) return;
        var ppoiField = document.querySelector('#' + field.dataset.ppoiId);
        if (!ppoiField) return;

        var point = field.querySelector('.imagefield-point'),
          img = e.target;
        x = e.offsetX / img.clientWidth;
        y = e.offsetY / img.clientHeight;
        ppoiField.value = x.toFixed(3) + 'x' + y.toFixed(3);
        movePoint(point, img, x, y);
      }
    });

  }

  window.addEventListener('load', centerpointWidget);

})();
