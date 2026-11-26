(() => {
  const path = location.pathname.toLowerCase();
  const items = [
    { href: "index.html", label: "Edges", paths: ["/", "/index.html"], icon: "M4 10 12 4l8 6v10H4z" },
    { href: "index.html#scoreboard", label: "Games", paths: ["/", "/index.html"], icon: "M3 5h18v14H3z M8 9h.01 M12 9h.01 M16 9h.01 M7 14h10" },
    { href: "bets.html", label: "Props", paths: ["/bets.html"], icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0" },
    { href: "history.html", label: "Results", paths: ["/history.html"], icon: "M3 3v18h18 M7 14l4-4 3 3 6-7" },
    { href: "index.html#fd-more", label: "More", paths: ["/model-lab.html", "/pipeline-health.html"], icon: "M5 7h14M5 12h14M5 17h14" }
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
