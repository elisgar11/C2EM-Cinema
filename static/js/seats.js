(() => {
    const form = document.querySelector("#seat-form");
    if (!form) return;

    const seats = [...form.querySelectorAll(".seat-input:not(:disabled)")];
    const count = document.querySelector("#selected-count");
    const total = document.querySelector("#selected-total");
    const submit = document.querySelector("#seat-submit");
    const price = Number(form.dataset.price.replace(",", "."));
    const currency = form.dataset.currency || "€";

    function refresh() {
        const selected = seats.filter((seat) => seat.checked).length;
        count.textContent = `${selected} butaca${selected === 1 ? "" : "s"}`;
        total.textContent = `${(selected * price).toFixed(2).replace(".", ",")}${currency}`;
        submit.disabled = selected === 0;
    }

    seats.forEach((seat) => seat.addEventListener("change", refresh));
    refresh();
})();
