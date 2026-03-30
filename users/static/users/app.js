(() => {
  const forms = Array.from(document.querySelectorAll("form[data-endpoint]"));
  if (!forms.length) return;

  const setResult = (form, message, isError = false) => {
    const result = form.closest(".auth-neo__card")?.querySelector("[data-result]")
      || form.querySelector("[data-result]")
      || document.querySelector("[data-result]");
    if (!result) return;
    result.textContent = message || "";
    result.style.color = isError ? "#b42318" : "#0a4a2b";
  };

  const collectFormData = (form) => {
    const data = {};
    new FormData(form).forEach((value, key) => {
      if (data[key] !== undefined) return;
      data[key] = value;
    });
    return data;
  };

  forms.forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const endpoint = form.getAttribute("data-endpoint") || form.getAttribute("action");
      const method = (form.getAttribute("data-method") || form.getAttribute("method") || "POST").toUpperCase();
      const redirectTo = form.getAttribute("data-redirect");

      const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
      const csrfToken = csrfInput ? csrfInput.value : null;

      const headers = {
        "Content-Type": "application/json",
      };
      if (csrfToken) headers["X-CSRFToken"] = csrfToken;

      const body = method === "GET" ? undefined : JSON.stringify(collectFormData(form));

      try {
        const response = await fetch(endpoint, {
          method,
          headers,
          body,
          credentials: "same-origin",
        });

        const payload = await response.json().catch(() => ({}));

        if (!response.ok || payload.success === false) {
          const message = payload.error || payload.message || "Não foi possível concluir.";
          setResult(form, message, true);
          return;
        }

        if (redirectTo) {
          window.location.assign(redirectTo);
          return;
        }

        const message = payload.message || "Concluído com sucesso.";
        setResult(form, message, false);
      } catch (err) {
        setResult(form, "Erro de conexão. Tente novamente.", true);
      }
    });
  });
})();
