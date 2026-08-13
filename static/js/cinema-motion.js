(() => {
    const root = document.documentElement;
    root.classList.add("js");

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const header = document.querySelector(".cinema-header");

    function updateHeader() {
        if (!header) return;
        header.classList.toggle("is-scrolled", window.scrollY > 18);
    }

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });

    const selectors = [
        ".section-heading",
        ".movie-card",
        ".cinema-schedule-group",
        ".cinema-synopsis-panel",
        ".cinema-cast-panel",
        ".screening-day",
        ".shop-card",
        ".summary-card",
        ".customer-form",
        ".ticket",
        ".ticket-staff",
        ".lookup-card",
        ".session-dashboard-card",
        ".dashboard-kpi",
        ".dashboard-panel",
        ".scanner-camera-card",
        ".scanner-manual-card",
        ".scanner-result",
        ".ad-card",
        ".cinema-ad",
        ".empty-state"
    ];

    const targets = Array.from(document.querySelectorAll(selectors.join(",")));
    targets.forEach((element, index) => {
        element.classList.add("c2em-reveal");
        element.style.setProperty("--reveal-order", String(index % 6));
    });

    if (reducedMotion || !("IntersectionObserver" in window)) {
        targets.forEach((element) => element.classList.add("is-visible"));
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
        });
    }, {
        rootMargin: "0px 0px -8% 0px",
        threshold: 0.08,
    });

    targets.forEach((element) => observer.observe(element));
})();
