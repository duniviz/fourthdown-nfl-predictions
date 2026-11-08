(() => {
  const path = location.pathname.toLowerCase();
  const items = [
    { href: "index.html", label: "Games", paths: ["/", "/index.html"], icon: "M3 5h18v14H3z M8 9h.01 M12 9h.01 M16 9h.01 M7 14h10" },
    { href: "bets.html", label: "Players", paths: ["/bets.html"], icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0" },
    { href: "history.html", label: "Accuracy", paths: ["/history.html"], icon: "M3 3v18h18 M7 14l4-4 3 3 6-7" },
    { href: "model-lab.html", label: "Labs", paths: ["/model-lab.html"], icon: "M4 19V5m0 14h17 M8 15l3-4 3 2 5-7" }
  ];
  const nav = document.createElement("nav");
  nav.className = "fd-app-nav";
  nav.setAttribute("aria-label", "Primary mobile navigation");
  nav.innerHTML = items.map(item => {
    const active = item.paths.includes(path);
    return `<a href="${item.href}"${active ? ' aria-current="page"' : ""}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${item.icon}"/></svg><span>${item.label}</span></a>`;
  }).join("");
  document.body.append(nav);
})();
