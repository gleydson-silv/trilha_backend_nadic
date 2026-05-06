# FlowCRM | Premium Studio Marketplace 🛍️

[![Django](https://img.shields.io/badge/Django-6.0-092e20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-REST_Framework-red?style=for-the-badge&logo=django)](https://www.django-rest-framework.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla-yellow?style=for-the-badge&logo=javascript)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![CSS3](https://img.shields.io/badge/CSS3-Studio_Style-blue?style=for-the-badge&logo=css3)](https://developer.mozilla.org/en-US/docs/Web/CSS)

O **FlowCRM** é uma plataforma de marketplace de luxo projetada para oferecer uma experiência de compra minimalista e uma gestão de vendas simplificada. Combinando o poder do **Django REST Framework** no backend com uma interface **Neo-Minimalista** no frontend, o projeto redefine a interação entre vendedores e clientes.

---

## ✨ Principais Funcionalidades

### 👤 Gestão de Perfis Híbridos
- **Dual-Role Engine**: Sistema de papéis dinâmicos (Vendedor vs. Cliente) com fluxos de cadastro e completude de perfil personalizados.
- **Segurança Avançada**: Autenticação via JWT e Suporte a **2FA (Autenticação em Duas Etapas)**.
- **Central de Conta**: Edição de dados em tempo real com validações rigorosas de CPF/CNPJ e endereços via integração com CEP.

### 🏪 Experiência do Cliente (Storefront)
- **Studio Interface**: Vitrine com design premium, transições suaves e grid responsivo.
- **Busca & Filtros**: Sistema de filtragem inteligente por categorias e pesquisa por texto.
- **Product Details**: Páginas de produto em layout "Split-screen" com foco total na imagem e informações essenciais.

### 🛒 Carrinho & Checkout
- **Cart Drawer**: Carrinho lateral persistente (LocalStorage) que permite adicionar itens sem recarregar a página.
- **Checkout Atômico**: Processamento de pedidos com transações de banco de dados para garantir integridade.
- **Gestão de Estoque Automática**: Baixa automática de produtos no momento da compra com verificação de disponibilidade em tempo real.

### 📊 Painel do Vendedor
- **Inventory Management**: CRUD completo de produtos com suporte a **Upload de Imagens Reais**.
- **Sales Insights**: (Preview) Acompanhamento de faturamento e desempenho de vendas.

---

## 🛠️ Stack Tecnológica

- **Backend**: Python 3.12 + Django 6.0
- **API**: Django REST Framework + SimpleJWT (Tokens)
- **Database**: SQLite (Desenvolvimento) / PostgreSQL (Recomendado para Produção)
- **Frontend**: HTML5, Vanilla CSS (Design System Studio), JavaScript (AJAX/Fetch API)
- **Imagens**: Pillow (Processamento de arquivos estáticos e mídia)

---

## 🚀 Como Executar o Projeto

1. **Clonar o Repositório**:
   ```bash
   git clone https://github.com/gleydson-silv/trilha_backend_nadic.git
   cd trilha_backend_nadic
   ```

2. **Configurar Ambiente Virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate   # Windows
   ```

3. **Instalar Dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Executar Migrações**:
   ```bash
   python manage.py migrate
   ```

5. **Iniciar o Servidor**:
   ```bash
   python manage.py runserver
   ```

6. **Acesse**: `http://127.0.0.1:8000/app/store/`

---

## 🎨 Filosofia de Design

O projeto segue a estética **"Studio"**:
- **Tipografia**: Uso das fontes *Inter* e *DM Serif Display* para contraste entre modernidade e elegância.
- **Paleta de Cores**: Tons neutros, sombras suaves (0 10px 30px rgba(0,0,0,0.02)) e bordas generosas de `24px`.
- **Micro-interações**: Hover effects em cards e botões com estados de loading integrados.

---

## 🛡️ Segurança

O FlowCRM implementa:
- Proteção contra **CSRF** em todas as requisições AJAX.
- Limitação de taxa (**Ratelimit**) para prevenir ataques de força bruta.
- Validação rigorosa de dados no servidor via **Django Validators**.

---

