// Intercept HTMX requests on changelog headers to handle toggle behavior.
// If content is already loaded, toggle client-side instead of re-fetching.
document.addEventListener("htmx:configRequest", function (event) {
  var header = event.detail.elt;
  if (!header.classList.contains("changelog-version-header")) return;

  var versionDiv = header.closest(".changelog-version");
  var content = versionDiv.querySelector(".changelog-content");
  var chevron = header.querySelector(".changelog-chevron");
  var detailDiv = content.querySelector("[id^='changelog-detail-']");
  var isExpanded = content.classList.contains("expanded");
  var hasContent = detailDiv && detailDiv.innerHTML.trim();

  if (isExpanded && hasContent) {
    // Expanded with content — collapse client-side, cancel HTMX request
    content.classList.remove("expanded");
    chevron.classList.remove("expanded");
    event.preventDefault();
    return;
  }

  if (!isExpanded && hasContent) {
    // Collapsed but already loaded — expand client-side, cancel HTMX request
    content.classList.add("expanded");
    chevron.classList.add("expanded");
    event.preventDefault();
    return;
  }

  // Not yet loaded — let HTMX fetch. Pre-expand so transition starts.
  content.classList.add("expanded");
  chevron.classList.add("expanded");
});

// After HTMX swaps in new content, ensure the container is expanded.
document.addEventListener("htmx:afterSwap", function (event) {
  var target = event.detail.target;
  if (!target || !target.id || !target.id.startsWith("changelog-detail-")) return;

  var content = target.closest(".changelog-content");
  if (content && !content.classList.contains("expanded")) {
    content.classList.add("expanded");
    var header = content.previousElementSibling;
    if (header) {
      var chevron = header.querySelector(".changelog-chevron");
      if (chevron) chevron.classList.add("expanded");
    }
  }
});
