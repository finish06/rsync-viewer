document.addEventListener("htmx:configRequest", function (event) {
  var header = event.detail.elt;
  if (!header.classList.contains("changelog-version-header")) return;

  var targetId = header.getAttribute("hx-target");
  if (!targetId) return;

  var target = document.querySelector(targetId);
  if (target && target.innerHTML.trim()) {
    target.innerHTML = "";
    event.preventDefault();
  }
});
