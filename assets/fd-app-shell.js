(() => {
  const path = location.pathname.toLowerCase();
  const items = [
    { href: "index.html#fd-slate-pulse", label: "Games", paths: [], icon: "M3 5h18v14H3z M8 9h.01 M12 9h.01 M16 9h.01 M7 14h10" },
    { href: "bets.html", label: "Props", paths: ["/bets.html"], icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0" },
    { href: "history.html", label: "Results", paths: ["/history.html"], icon: "M3 3v18h18 M7 14l4-4 3 3 6-7" },
    { href: "model-lab.html", label: "Labs", paths: ["/model-lab.html"], icon: "M9 3h6 M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3 M8 15h8" }
  ];
  const nav = document.createElement("nav");
  nav.className = "fd-app-nav";
  nav.setAttribute("aria-label", "Primary mobile navigation");
  nav.innerHTML = items.map(item => {
    const active = item.paths.some(page => path === page || path.endsWith(page));
    return `<a href="${item.href}"${active ? ' aria-current="page"' : ""}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${item.icon}"/></svg><span>${item.label}</span></a>`;
  }).join("");
  document.body.append(nav);
})();
