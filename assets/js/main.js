// Mostra Científica da Rede Municipal de Ensino — Caxias do Sul — Edição 2026

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const menu = document.querySelector(".nav-menu");

  if (toggle && menu) {
    toggle.addEventListener("click", () => {
      menu.classList.toggle("open");
    });

    menu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => menu.classList.remove("open"));
    });
  }

  // Marca o item de navegação da página atual
  const current = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-menu a").forEach((link) => {
    const href = link.getAttribute("href");
    if (href === current) {
      link.classList.add("active");
    }
  });

  // Formulário de contato (front-end apenas — sem backend configurado)
  const contactForm = document.querySelector("#form-contato");
  if (contactForm) {
    contactForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const status = contactForm.querySelector(".form-status");
      status.textContent = "Mensagem enviada! Em breve entraremos em contato.";
      status.classList.add("show", "ok");
      contactForm.reset();
    });
  }
});
