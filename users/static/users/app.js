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

  const loadCategories = async () => {
    const select = document.getElementById("category-select");
    if (!select) return;

    // Se já tiver opções (mais que a padrão de 'Carregando'), não sobrescreve
    if (select.options.length > 1) return;

    try {
      const response = await fetch("/categories/");
      const result = await response.json();
      if (result.success) {
        select.innerHTML = '<option value="">Selecione uma categoria</option>';
        result.data.results.forEach((cat) => {
          const option = document.createElement("option");
          option.value = cat.id;
          option.textContent = cat.name;
          select.appendChild(option);
        });
      }
    } catch (error) {
      select.innerHTML = '<option value="">Erro ao carregar categorias</option>';
    }
  };

  const loadSalesReport = async () => {
    const amountEl = document.getElementById("revenue-amount");
    if (!amountEl) return;

    const token = localStorage.getItem("access");
    if (!token) return;

    try {
      const response = await fetch("/reports/revenue/", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        const amount = data.data.total_revenue;
        amountEl.textContent = `R$ ${parseFloat(amount).toLocaleString("pt-BR", {
          minimumFractionDigits: 2,
        })}`;
        
        // Se houver um container de histórico, podemos atualizar também
        const historyContainer = document.querySelector(".profile__card .text-center");
        if (historyContainer) {
            historyContainer.textContent = "Relatório atualizado com sucesso.";
        }
      }
    } catch (error) {
      console.error("Erro ao buscar faturamento:", error);
    }
  };

  const clearFieldErrors = (form) => {
    form.querySelectorAll(".field-error").forEach((el) => el.remove());
    form.querySelectorAll(".auth-neo__field").forEach((el) => {
      el.classList.remove("has-error");
    });
  };

  const showFieldErrors = (form, errors) => {
    // A API pode retornar um objeto { field: [errors] } ou { detail: "msg" }
    for (const [field, messages] of Object.entries(errors)) {
      const input = form.querySelector(`[name="${field}"]`);
      if (input) {
        const fieldContainer = input.closest(".auth-neo__field");
        const errorMessage = Array.isArray(messages) ? messages[0] : messages;

        const errorEl = document.createElement("span");
        errorEl.className = "field-error";
        errorEl.textContent = errorMessage;

        if (fieldContainer) {
          fieldContainer.appendChild(errorEl);
          fieldContainer.classList.add("has-error");
        } else {
          input.after(errorEl);
        }
      }
    }
  };

  const setResult = (form, message, isError = false) => {
    const result =
      form.closest(".auth-neo__card")?.querySelector("[data-result]") ||
      form.querySelector("[data-result]") ||
      document.querySelector("[data-result]") ||
      document.getElementById("form-message");
    if (!result) return;
    result.textContent = message || "";
    result.style.color = isError ? "#b42318" : "#0a4a2b";
    
    // Suporte para classes específicas de mensagem se existirem
    if (isError) {
        result.classList.add('auth-neo__message--error');
        result.classList.remove('auth-neo__message--success');
    } else {
        result.classList.add('auth-neo__message--success');
        result.classList.remove('auth-neo__message--error');
    }
  };

  const collectFormData = (form) => {
    const data = {};
    new FormData(form).forEach((value, key) => {
      if (data[key] !== undefined) return;
      
      // Conversões automáticas para campos conhecidos
      if (key === "price") {
          data[key] = parseFloat(value) || 0;
      } else if (key === "quantity_in_stock" || key === "category") {
          data[key] = parseInt(value) || 0;
      } else {
          data[key] = value;
      }
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

  // Inicialização
  document.addEventListener("DOMContentLoaded", () => {
    setupCompleteProfileForm();
    loadCategories();
    loadSalesReport();

    const forms = Array.from(document.querySelectorAll("form[data-endpoint]"));
    forms.forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const endpoint =
          form.getAttribute("data-endpoint") || form.getAttribute("action");
        const method = (
          form.getAttribute("data-method") ||
          form.getAttribute("method") ||
          "POST"
        ).toUpperCase();
        const redirectTo = form.getAttribute("data-redirect");

        const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;
        const accessToken = localStorage.getItem("access");

        const fileInput = form.querySelector('input[type="file"]');
        const hasFile = fileInput && fileInput.files.length > 0;

        const headers = {};
        if (csrfToken) headers["X-CSRFToken"] = csrfToken;
        if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

        let body;
        if (method === "GET" || method === "DELETE") {
          body = undefined;
        } else if (hasFile) {
          // FormData para upload (O navegador define o Content-Type com boundary automaticamente)
          body = new FormData(form);
        } else {
          headers["Content-Type"] = "application/json";
          body = JSON.stringify(collectFormData(form));
        }

        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) submitBtn.classList.add("btn--loading");

        clearFieldErrors(form);
        setResult(form, "Processando...");

        try {
          const response = await fetch(endpoint, {
            method,
            headers,
            body,
            credentials: "same-origin",
          });

          if (submitBtn) submitBtn.classList.remove("btn--loading");

          const payload = await response.json().catch(() => ({}));

          if (!response.ok || payload.success === false) {
            // Se for um erro de validação (objeto com campos), mostra nos campos
            if (response.status === 400 && typeof payload === "object") {
              // Se a API retornar { "success": false, "error": { ... } }
              const fieldErrors = payload.error || payload;
              showFieldErrors(form, fieldErrors);
            }
            
            const message =
              payload.message || payload.error || "Não foi possível concluir.";
            setResult(form, message, true);
            return;
          }

          // Store tokens if present (Login/Register)
          if (payload.data) {
            if (payload.data.access)
              localStorage.setItem("access", payload.data.access);
            if (payload.data.refresh)
              localStorage.setItem("refresh", payload.data.refresh);
          }

          if (redirectTo) {
            setResult(form, payload.message || "Sucesso! Redirecionando...");
            setTimeout(() => {
                let redirectTarget = redirectTo;
                const roleField =
                  form.querySelector('[name="role"]') ||
                  form.querySelector('[name="user_type"]');
                const role = normalizeRole(roleField?.value);
                if (role) {
                  const url = new URL(redirectTo, window.location.origin);
                  if (!url.searchParams.get("role")) {
                    url.searchParams.set("role", role);
                  }
                  redirectTarget = `${url.pathname}${url.search}${url.hash}`;
                }
                window.location.assign(redirectTarget);
            }, 1500);
            return;
          }

          const message = payload.message || "Concluído com sucesso.";
          setResult(form, message, false);
        } catch (err) {
          setResult(form, "Erro de conexão. Tente novamente.", true);
        }
      });
    });
  });
})();

  // --- Shopping Cart Logic ---
  const cartManager = {
    items: JSON.parse(localStorage.getItem('cart')) || [],
    
    init() {
      this.updateUI();
      this.bindEvents();
    },

    save() {
      localStorage.setItem('cart', JSON.stringify(this.items));
      this.updateUI();
    },

    addItem(product) {
      const existing = this.items.find(item => item.id === product.id);
      if (existing) {
        existing.quantity += 1;
      } else {
        this.items.push({ ...product, quantity: 1 });
      }
      this.save();
      this.openDrawer();
    },

    removeItem(id) {
      this.items = this.items.filter(item => item.id !== id);
      this.save();
    },

    updateUI() {
      const countEl = document.getElementById('cart-count');
      const itemsContainer = document.getElementById('cart-items');
      const totalEl = document.getElementById('cart-total');
      
      if (!countEl || !itemsContainer) return;

      const totalItems = this.items.reduce((sum, item) => sum + item.quantity, 0);
      countEl.textContent = totalItems;

      if (this.items.length === 0) {
        itemsContainer.innerHTML = '<p class="muted text-center py-40">Seu carrinho está vazio.</p>';
        totalEl.textContent = 'R$ 0,00';
        return;
      }

      let total = 0;
      itemsContainer.innerHTML = this.items.map(item => {
        const itemTotal = parseFloat(item.price) * item.quantity;
        total += itemTotal;
        return `
          <div class="cart-item">
            <img src="${item.image || '/static/users/logo2.png'}" class="cart-item__img">
            <div class="cart-item__info">
              <h4>${item.name}</h4>
              <p>${item.quantity}x R$ ${parseFloat(item.price).toFixed(2)}</p>
              <button class="cart-item__remove" onclick="window.cartManager.removeItem('${item.id}')">Remover</button>
            </div>
          </div>
        `;
      }).join('');

      totalEl.textContent = `R$ ${total.toFixed(2)}`;
    },

    openDrawer() {
      document.getElementById('cart-drawer')?.classList.add('drawer--open');
    },

    closeDrawer() {
      document.getElementById('cart-drawer')?.classList.remove('drawer--open');
    },

    getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    },

    async checkout() {
      if (this.items.length === 0) return;

      const checkoutBtn = document.getElementById('checkout-btn');
      if (checkoutBtn) {
        checkoutBtn.disabled = true;
        checkoutBtn.textContent = 'Processando...';
      }

      const payload = {
        items: this.items.map(item => ({
          product_id: parseInt(item.id),
          quantity: item.quantity
        })),
        payment_method: 'pix'
      };

      try {
        const response = await fetch('/api/checkout/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCookie('csrftoken')
          },
          body: JSON.stringify(payload),
          credentials: 'same-origin'
        });

        const data = await response.json();

        if (response.ok) {
          alert('Pedido realizado com sucesso! Seu estoque foi atualizado.');
          this.items = [];
          this.save();
          this.closeDrawer();
          window.location.href = '/app/store/';
        } else {
          alert('Erro ao finalizar: ' + (data.message || data.error || 'Tente novamente.'));
        }
      } catch (err) {
        alert('Erro de conexão. Verifique sua internet.');
      } finally {
        if (checkoutBtn) {
          checkoutBtn.disabled = false;
          checkoutBtn.textContent = 'Finalizar Compra';
        }
      }
    },

    bindEvents() {
      document.getElementById('open-cart')?.addEventListener('click', () => this.openDrawer());
      document.getElementById('close-cart')?.addEventListener('click', () => this.closeDrawer());
      document.getElementById('close-cart-overlay')?.addEventListener('click', () => this.closeDrawer());
      document.getElementById('checkout-btn')?.addEventListener('click', () => this.checkout());

      document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-add-cart]');
        if (btn) {
          const product = {
            id: btn.dataset.addCart,
            name: btn.dataset.name,
            price: btn.dataset.price,
            image: btn.dataset.image
          };
          this.addItem(product);
        }
      });
    }
  };

  window.cartManager = cartManager;
  cartManager.init();
