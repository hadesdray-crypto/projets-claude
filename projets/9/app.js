(function () {
  "use strict";

  // --- Menu ---
  var menu = document.getElementById("menu");
  var ouvrir = document.getElementById("btn-menu");
  function fermer() {
    menu.hidden = true;
    ouvrir.setAttribute("aria-expanded", "false");
    document.body.classList.remove("menu-ouvert");
    ouvrir.focus();
  }
  ouvrir.addEventListener("click", function () {
    menu.hidden = false;
    ouvrir.setAttribute("aria-expanded", "true");
    document.body.classList.add("menu-ouvert");
    menu.querySelector(".menu-feuille a").focus();
  });
  menu.addEventListener("click", function (e) {
    if (e.target.closest("[data-fermer]")) { fermer(); }
    else if (e.target.closest("a")) {
      menu.hidden = true;
      ouvrir.setAttribute("aria-expanded", "false");
      document.body.classList.remove("menu-ouvert");
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !menu.hidden) { fermer(); }
  });

  // --- Images : images.json remplace les illustrations par des photos ---
  fetch("images.json").then(function (r) { return r.json(); }).then(function (cfg) {
    document.querySelectorAll("[data-image]").forEach(function (fig) {
      var c = cfg[fig.getAttribute("data-image")];
      if (!c) { return; }
      var img = fig.querySelector("img");
      img.alt = c.alt || "";
      if (c.fichier) {
        img.src = "images/" + c.fichier;
        var l = fig.querySelector("figcaption");
        if (l) { l.remove(); }
      } else if (c.illustration) {
        img.src = c.illustration;
      }
    });
  }).catch(function () { /* hors serveur : les illustrations par défaut restent */ });
})();
