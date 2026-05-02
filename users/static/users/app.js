(() => {
  const normalizeRole = (value) => {
    if (!value) return null;
    const role = String(value).trim().toLowerCase();
    if (role === "cliente" || role === "customer") return "customer";
    if (role === "vendedor" || role === "seller") return "seller";
    return null;
  };

  const toggleField = (input, shouldShow, isRequired) => {
    if (!input) return;
    const wrapper = input.closest(".auth-neo__field") || input.parentElement;
    if (wrapper) wrapper.style.display = shouldShow ? "" : "none";
    input.required = Boolean(isRequired);
  };

  const setupCompleteProfileForm = () => {
    const form = document.querySelector('form[data-endpoint="/profile/complete/"]');
    if (!form) return;

    const params = new URLSearchParams(window.location.search);
    const role = normalizeRole(params.get("role") || params.get("user_type"));
    if (!role) return;

    const cpfInput = form.querySelector('input[name="cpf"]');
    const companyInput = form.querySelector('input[name="company_name"]');
    const cnpjInput = form.querySelector('input[name="cnpj"]');

    if (role === "customer") {
      toggleField(cpfInput, true, true);
      toggleField(companyInput, false, false);
      toggleField(cnpjInput, false, false);
      return;
    }

    if (role === "seller") {
      toggleField(cpfInput, false, false);
      toggleField(companyInput, true, true);
      toggleField(cnpjInput, true, true);
    }
  };

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

    const userType = data.user_type;
    const role = normalizeRole(userType);
    if (role && !data.role) {
      data.role = role;
    }
    if (data.user_type && role) {
      delete data.user_type;
    }

    return data;
  };

  setupCompleteProfileForm();

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

        // Store tokens if present (Login/Register)
        if (payload.data) {
          if (payload.data.access) localStorage.setItem('access', payload.data.access);
          if (payload.data.refresh) localStorage.setItem('refresh', payload.data.refresh);
        }

        if (redirectTo) {
          let redirectTarget = redirectTo;
          const roleField = form.querySelector('[name="role"]') || form.querySelector('[name="user_type"]');
          const role = normalizeRole(roleField?.value);
          if (role) {
            const url = new URL(redirectTo, window.location.origin);
            if (!url.searchParams.get("role")) {
              url.searchParams.set("role", role);
            }
            redirectTarget = `${url.pathname}${url.search}${url.hash}`;
          }
          window.location.assign(redirectTarget);
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
