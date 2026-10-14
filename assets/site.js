/* Shared helpers for vptpoints.com tool pages: navigation, data loading, formatting, tables and charts. */
(function () {
  "use strict";

  // Navigation: phone menu toggle and the desktop "More" dropdown.
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".site-nav");
  var more = document.querySelector(".more");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }
  if (more) {
    var btn = more.querySelector(".more-btn");
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = more.classList.toggle("open");
      btn.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", function (e) {
      if (!more.contains(e.target)) { more.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { more.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); }
    });
  }

  // Opened from disk, a link to a folder ("../rounds/") shows a directory
  // listing, so point it at the folder's index.html instead.
  if (location.protocol === "file:") {
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("a[href]");
      if (!a || /^[a-z]+:/i.test(a.getAttribute("href")) || a.getAttribute("href").charAt(0) === "#") return;
      var u = new URL(a.href);
      if (u.protocol === "file:" && /\/$/.test(u.pathname)) { u.pathname += "index.html"; a.href = u.href; }
    }, true);
  }

  var VPT = window.VPT = {};

  VPT.$ = function (sel, root) { return (root || document).querySelector(sel); };
  VPT.esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  VPT.plural = function (n, word, many) { return VPT.num(n) + " " + (n === 1 ? word : many || word + "s"); };
  VPT.num = function (n) { return n == null || n === "" || isNaN(n) ? "–" : Number(n).toLocaleString("en-AU"); };
  VPT.compact = function (n) {
    if (n == null) return "–";
    var a = Math.abs(n);
    if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
    if (a >= 1e3) return (n / 1e3).toFixed(a >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "K";
    return String(n);
  };
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  VPT.date = function (iso, short) {
    if (!iso) return "–";
    var p = String(iso).split("-");
    if (p.length === 2) return MONTHS[+p[1] - 1] + " " + p[0];
    return (+p[2]) + " " + MONTHS[+p[1] - 1] + (short ? " " + p[0].slice(2) : " " + p[0]);
  };
  VPT.daysBetween = function (a, b) { return Math.round((Date.parse(b) - Date.parse(a)) / 864e5); };
  VPT.today = function () { var d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); };

  // Data files live in /data. Pages pass a path relative to themselves.
  // Opened from disk (file://), browsers block fetch(), so load the matching
  // data/*.js copy with a script tag instead (scripts/layout.py writes them).
  var cache = {};
  function loadScript(path) {
    var name = path.split("/").pop().replace(/\.json$/, "");
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = path.replace(/\.json$/, ".js");
      s.onload = function () { var d = (window.VPT_DATA || {})[name]; d ? resolve(d) : reject(new Error(path + " has no data")); };
      s.onerror = function () { reject(new Error(s.src + " failed to load")); };
      document.head.appendChild(s);
    });
  }
  VPT.load = function (path) {
    if (!cache[path]) cache[path] = location.protocol === "file:" ? loadScript(path) : fetch(path, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(path + " " + r.status);
      return r.json();
    });
    return cache[path];
  };
  VPT.sources = function (el, data) {
    if (!el || !data) return;
    var s = (data.sources || []).map(function (x) { return '<a href="' + VPT.esc(x.url) + '" rel="noopener">' + VPT.esc(x.label) + "</a>"; }).join(" · ");
    el.innerHTML = "Source: " + (s || "official publications") + (data.updated ? " · Checked " + VPT.date(data.updated) : "");
  };
  VPT.fail = function (el, err) {
    if (el) el.innerHTML = '<div class="empty">This data couldn’t be loaded. Refresh the page to try again.</div>';
    if (window.console) console.error(err);
  };

  // localStorage wrapper that never throws (private mode, blocked storage).
  VPT.store = {
    get: function (k, d) { try { var v = localStorage.getItem("vpt:" + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem("vpt:" + k, JSON.stringify(v)); } catch (e) {} }
  };

  // Saved occupations shared by Occupations, Compare and 189 chances.
  VPT.saved = {
    list: function () { return VPT.store.get("saved", []); },
    has: function (code) { return VPT.saved.list().indexOf(code) >= 0; },
    toggle: function (code) {
      var l = VPT.saved.list(), i = l.indexOf(code);
      if (i >= 0) l.splice(i, 1); else { l.push(code); if (l.length > 4) l.shift(); }
      VPT.store.set("saved", l);
      return i < 0;
    }
  };

  // Sortable table. cols: [{key, label, num, render(row)}]. Returns {render(rows)}.
  VPT.table = function (el, cols, opts) {
    opts = opts || {};
    var sortKey = opts.sortKey || null, dir = opts.dir || 1, rows = [];
    function draw() {
      var data = rows.slice();
      if (sortKey) {
        data.sort(function (a, b) {
          var x = a[sortKey], y = b[sortKey];
          if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
          return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * dir;
        });
      }
      var limit = opts.limit || Infinity, shown = data.slice(0, limit);
      var h = '<table class="data"><thead><tr>' + cols.map(function (c) {
        var s = c.key === sortKey ? (dir > 0 ? "ascending" : "descending") : "none";
        return '<th scope="col" class="' + (c.num ? "num" : "") + '" aria-sort="' + s + '">' + (c.nosort ? VPT.esc(c.label) : '<button type="button" data-k="' + c.key + '">' + VPT.esc(c.label) + "</button>") + "</th>";
      }).join("") + "</tr></thead><tbody>";
      h += shown.length ? shown.map(function (r) {
        return "<tr>" + cols.map(function (c) {
          var v = c.render ? c.render(r) : (c.num ? VPT.num(r[c.key]) : VPT.esc(r[c.key] == null ? "–" : r[c.key]));
          return '<td class="' + (c.num ? "num" : "") + '">' + v + "</td>";
        }).join("") + "</tr>";
      }).join("") : '<tr><td colspan="' + cols.length + '" class="empty">' + (opts.empty || "Nothing matches.") + "</td></tr>";
      h += "</tbody></table>";
      el.innerHTML = h;
      if (opts.onDraw) opts.onDraw(data.length, shown.length);
    }
    el.addEventListener("click", function (e) {
      var b = e.target.closest("th button");
      if (!b) return;
      var k = b.getAttribute("data-k");
      if (k === sortKey) dir = -dir; else { sortKey = k; dir = cols.filter(function (c) { return c.key === k; })[0].num ? -1 : 1; }
      draw();
    });
    return { render: function (r) { rows = r || []; draw(); } };
  };

  // Charts: plain SVG with a hover tooltip. Columns (one or two series) and lines.
  // spec: {labels:[], series:[{name, color:'var(--s1)', values:[]}], type:'col'|'line', height, yMin, fmt}
  VPT.chart = function (el, spec) {
    var W = Math.max(el.clientWidth || 640, 300), H = spec.height || 260;
    var m = { t: 18, r: 12, b: 34, l: 44 };
    var iw = W - m.l - m.r, ih = H - m.t - m.b;
    var all = [];
    spec.series.forEach(function (s) { s.values.forEach(function (v) { if (v != null) all.push(v); }); });
    if (!all.length) { el.innerHTML = '<div class="empty">No data yet.</div>'; return; }
    var lo = spec.yMin != null ? spec.yMin : 0, hi = Math.max.apply(null, all);
    var step = niceStep((hi - lo) / 4);
    hi = Math.ceil(hi / step) * step; if (hi === lo) hi = lo + step;
    lo = Math.floor(lo / step) * step;
    var y = function (v) { return m.t + ih - (v - lo) / (hi - lo) * ih; };
    var n = spec.labels.length, band = iw / n;
    var x = function (i) { return m.l + band * i + band / 2; };
    var fmt = spec.fmt || VPT.compact;
    var svg = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + VPT.esc(spec.title || "Chart") + '">';
    svg += '<g class="axis">';
    for (var t = lo; t <= hi + 1e-9; t += step) {
      svg += '<line class="gridline" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y(t) + '" y2="' + y(t) + '"/>';
      svg += '<text x="' + (m.l - 8) + '" y="' + (y(t) + 4) + '" text-anchor="end">' + fmt(t) + "</text>";
    }
    var every = Math.max(1, Math.ceil(n / Math.floor(iw / 64)));
    spec.labels.forEach(function (l, i) {
      if (i % every === 0 || i === n - 1 && (n - 1) % every > every / 2) svg += '<text x="' + x(i) + '" y="' + (H - 10) + '" text-anchor="middle">' + VPT.esc(l) + "</text>";
    });
    svg += "</g>";
    var k = spec.series.length;
    if (spec.type === "line") {
      spec.series.forEach(function (s) {
        var d = "", pen = false;
        s.values.forEach(function (v, i) { if (v == null) { pen = false; return; } d += (pen ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); pen = true; });
        svg += '<path d="' + d + '" fill="none" stroke="' + s.color + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
        s.values.forEach(function (v, i) { if (v != null) svg += '<circle cx="' + x(i) + '" cy="' + y(v) + '" r="4" fill="' + s.color + '" stroke="var(--card)" stroke-width="2"/>'; });
      });
    } else {
      var bw = Math.min(24, (band - 6) / k - 2);
      spec.series.forEach(function (s, si) {
        s.values.forEach(function (v, i) {
          if (v == null) return;
          var bx = x(i) - (bw * k + 2 * (k - 1)) / 2 + si * (bw + 2), top = y(v), base = y(lo), h = Math.max(base - top, 1), r = Math.min(4, h, bw / 2);
          svg += '<path fill="' + (spec.highlight === i ? "var(--sun)" : s.color) + '" d="M' + bx + " " + base + "V" + (top + r) + "q0 -" + r + " " + r + " -" + r + "h" + (bw - 2 * r) + "q" + r + " 0 " + r + " " + r + "V" + base + 'Z"/>';
        });
      });
    }
    // Invisible hit targets, one per label column.
    spec.labels.forEach(function (l, i) { svg += '<rect data-i="' + i + '" x="' + (m.l + band * i) + '" y="' + m.t + '" width="' + band + '" height="' + ih + '" fill="transparent"/>'; });
    svg += "</svg>";
    var legend = k > 1 ? '<ul class="chart-legend">' + spec.series.map(function (s) { return '<li><i style="background:' + s.color + '"></i>' + VPT.esc(s.name) + "</li>"; }).join("") + "</ul>" : "";
    el.innerHTML = legend + '<div class="chart">' + svg + '<div class="tip-box"></div></div>';
    var box = el.querySelector(".chart"), tip = el.querySelector(".tip-box"), svgEl = el.querySelector("svg");
    function show(i) {
      var vals = spec.series.map(function (s) { return s.values[i]; });
      var top = Math.min.apply(null, vals.filter(function (v) { return v != null; }).map(y));
      if (!isFinite(top)) { tip.classList.remove("on"); return; }
      var sc = svgEl.getBoundingClientRect().width / W;
      tip.innerHTML = "<b>" + VPT.esc(spec.tipLabels ? spec.tipLabels[i] : spec.labels[i]) + "</b>" + spec.series.map(function (s) {
        return "<br>" + (k > 1 ? VPT.esc(s.name) + ": " : "") + (s.values[i] == null ? "–" : VPT.num(s.values[i])) + (spec.unit ? " " + spec.unit : "");
      }).join("");
      tip.style.left = x(i) * sc + "px"; tip.style.top = top * sc + "px";
      tip.classList.add("on");
    }
    svgEl.addEventListener("mousemove", function (e) { var r = e.target.closest && e.target.closest("rect[data-i]"); if (r) show(+r.getAttribute("data-i")); });
    svgEl.addEventListener("mouseleave", function () { tip.classList.remove("on"); });
  };
  function niceStep(raw) {
    if (raw <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }

  // Horizontal bars for ranked lists (single series, brand colour).
  VPT.hbars = function (el, rows, opts) {
    opts = opts || {};
    var max = Math.max.apply(null, rows.map(function (r) { return r.value || 0; })) || 1;
    el.innerHTML = '<div class="hbar">' + rows.map(function (r) {
      return '<div class="hbar-row"><span class="name" title="' + VPT.esc(r.label) + '">' + VPT.esc(r.label) + '</span><span class="hbar-track"><span class="hbar-fill" style="width:' + (r.value / max * 82).toFixed(1) + '%"></span><b>' + VPT.num(r.value) + "</b></span></div>";
    }).join("") + "</div>";
  };


  // Joins the occupation list with round cut-offs, EOI counts and ceilings, keyed by ANZSCO code.
  VPT.occData = function (root) {
    return Promise.all(["occupations", "rounds", "eoi", "ceilings"].map(function (n) { return VPT.load(root + "data/" + n + ".json"); })).then(function (r) {
      var occ = r[0], rounds = r[1], eoi = r[2], ceil = r[3], by = {}, list = [];
      occ.occupations.forEach(function (o) {
        if (!o.anzsco) return;
        if (by[o.anzsco]) { by[o.anzsco].aka.push(o.name); return; }
        var x = Object.assign({ aka: [], history: [], cutoff: null, eoi: null, ceiling: null }, o);
        by[o.anzsco] = x; list.push(x);
      });
      (rounds.byOccupation || []).forEach(function (h) { if (h.anzsco && by[h.anzsco]) by[h.anzsco].history.push(h); });
      list.forEach(function (o) {
        o.history.sort(function (a, b) { return a.roundDate < b.roundDate ? -1 : 1; });
        var h189 = o.history.filter(function (h) { return h.subclass === "189" && h.minPoints >= 65; });
        o.cutoff = h189.length ? h189[h189.length - 1] : null;
      });
      (eoi.byOccupation || []).forEach(function (e) { if (by[e.anzsco]) by[e.anzsco].eoi = e; });
      var yr = (ceil.years || [])[0];
      if (yr) {
        var cu = {};
        yr.rows.forEach(function (c) { cu[c.unitGroup] = c; });
        list.forEach(function (o) { o.ceiling = cu[o.unitGroup || String(o.anzsco).slice(0, 4)] || null; });
      }
      var roundDates = (rounds.rounds || []).map(function (x) { return x.date; }).sort();
      return { list: list, by: by, rounds: rounds, eoi: eoi, ceil: ceil, occ: occ, ceilYear: yr ? yr.fy : null, roundDates: roundDates,
        latestRound: roundDates[roundDates.length - 1] };
    });
  };
  // Ceiling places left for 189; Home Affairs prints "-" when none are left.
  VPT.left = function (c) {
    if (!c) return "–";
    if (c.remaining189 != null) return VPT.num(c.remaining189);
    return c.remaining189Raw === "-" ? "None left" : VPT.esc(c.remaining189Raw || "–");
  };
  VPT.findOcc = function (D, q) {
    if (!q) return null;
    q = String(q).trim();
    if (D.by[q]) return D.by[q];
    var m = q.match(/\b(\d{6})\b/); if (m && D.by[m[1]]) return D.by[m[1]];
    var lq = q.toLowerCase();
    return D.list.filter(function (o) { return o.name.toLowerCase() === lq; })[0] || null;
  };

  // Redraw charts when the width changes.
  var redraws = [];
  VPT.onResize = function (fn) { redraws.push(fn); };
  var lastW = window.innerWidth, timer;
  window.addEventListener("resize", function () {
    if (window.innerWidth === lastW) return;
    lastW = window.innerWidth; clearTimeout(timer);
    timer = setTimeout(function () { redraws.forEach(function (f) { f(); }); }, 150);
  });
})();
