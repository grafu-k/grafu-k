// Feuerwehr St. Stefan ob Leoben – kleine Helfer (Menü, Galerie, Video, Kopieren)
(function () {
  "use strict";

  // ---------- Mobiles Menü ----------
  var knopf = document.querySelector(".menue-knopf");
  var nav = document.getElementById("hauptmenue");
  if (knopf && nav) {
    knopf.addEventListener("click", function () {
      var offen = nav.classList.toggle("offen");
      knopf.setAttribute("aria-expanded", offen);
      knopf.setAttribute("aria-label", offen ? "Menü schließen" : "Menü öffnen");
      document.body.classList.toggle("menue-offen", offen);
    });
  }
  document.querySelectorAll(".nav-oben").forEach(function (b) {
    b.addEventListener("click", function () {
      var li = b.parentElement;
      var offen = !li.classList.contains("offen");
      document.querySelectorAll(".nav-punkt.offen").forEach(function (x) {
        if (x !== li) { x.classList.remove("offen"); x.querySelector(".nav-oben").setAttribute("aria-expanded", "false"); }
      });
      li.classList.toggle("offen", offen);
      b.setAttribute("aria-expanded", offen);
    });
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".nav-punkt") && window.innerWidth > 900) {
      document.querySelectorAll(".nav-punkt.offen").forEach(function (x) { x.classList.remove("offen"); });
    }
  });

  // ---------- Bildergalerie + Vollbild ----------
  var lb, lbImg, lbBilder = [], lbIndex = 0;
  function lightbox() {
    if (lb) return;
    lb = document.createElement("div");
    lb.className = "lightbox";
    lb.hidden = true;
    lb.setAttribute("role", "dialog");
    lb.setAttribute("aria-label", "Bildansicht");
    lb.innerHTML = '<img alt=""><button class="lb-zu" aria-label="Schließen">✕</button><button class="lb-zurueck" aria-label="Vorheriges Bild">❮</button><button class="lb-weiter" aria-label="Nächstes Bild">❯</button>';
    document.body.appendChild(lb);
    lbImg = lb.querySelector("img");
    lb.querySelector(".lb-zu").onclick = schliessen;
    lb.querySelector(".lb-zurueck").onclick = function (e) { e.stopPropagation(); lbZeige(lbIndex - 1); };
    lb.querySelector(".lb-weiter").onclick = function (e) { e.stopPropagation(); lbZeige(lbIndex + 1); };
    lb.addEventListener("click", function (e) { if (e.target === lb) schliessen(); });
    document.addEventListener("keydown", function (e) {
      if (lb.hidden) return;
      if (e.key === "Escape") schliessen();
      if (e.key === "ArrowLeft") lbZeige(lbIndex - 1);
      if (e.key === "ArrowRight") lbZeige(lbIndex + 1);
    });
    wischen(lb, function (r) { lbZeige(lbIndex + r); });
  }
  function lbZeige(i) {
    lbIndex = (i + lbBilder.length) % lbBilder.length;
    lbImg.src = lbBilder[lbIndex];
    var mehrere = lbBilder.length > 1;
    lb.querySelector(".lb-zurueck").hidden = !mehrere;
    lb.querySelector(".lb-weiter").hidden = !mehrere;
  }
  function schliessen() { lb.hidden = true; document.body.style.overflow = ""; }
  function wischen(el, cb) {
    var x0 = null;
    el.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    el.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 45) cb(dx < 0 ? 1 : -1);
      x0 = null;
    });
  }

  document.querySelectorAll("[data-galerie]").forEach(function (g) {
    var bilder = Array.prototype.slice.call(g.querySelectorAll(".galerie-bild"));
    var nr = g.querySelector("[data-nr]");
    var akt = 0;
    function zeige(i) {
      akt = (i + bilder.length) % bilder.length;
      bilder.forEach(function (b, j) { b.classList.toggle("aktiv", j === akt); });
      if (nr) nr.textContent = akt + 1;
    }
    g.querySelectorAll(".galerie-pfeil").forEach(function (p) {
      p.addEventListener("click", function () { zeige(akt + Number(p.dataset.schritt)); });
    });
    bilder.forEach(function (b, j) {
      b.addEventListener("click", function () {
        lightbox();
        lbBilder = bilder.map(function (x) { return x.querySelector("img").src; });
        lbZeige(j);
        lb.hidden = false;
        document.body.style.overflow = "hidden";
      });
    });
    if (bilder.length > 1) wischen(g, function (r) { zeige(akt + r); });
  });

  // ---------- YouTube erst nach Klick laden (Datenschutz) ----------
  document.querySelectorAll("[data-youtube]").forEach(function (v) {
    var b = v.querySelector(".video-start");
    b.addEventListener("click", function () {
      var f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(v.dataset.youtube) + "?autoplay=1&rel=0&modestbranding=1&playsinline=1";
      f.title = "YouTube Video";
      f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      f.allowFullscreen = true;
      v.innerHTML = "";
      v.appendChild(f);
    });
  });

  // ---------- Kopieren (Spenden) ----------
  document.querySelectorAll("[data-kopieren]").forEach(function (el) {
    if (!navigator.clipboard) return;
    var k = document.createElement("button");
    k.type = "button";
    k.className = "kopieren-knopf";
    k.textContent = "Kopieren";
    k.addEventListener("click", function () {
      navigator.clipboard.writeText(el.textContent.trim()).then(function () {
        k.textContent = "Kopiert ✓";
        setTimeout(function () { k.textContent = "Kopieren"; }, 1800);
      });
    });
    el.after(k);
  });
})();
