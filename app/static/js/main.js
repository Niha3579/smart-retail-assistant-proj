/* Smart Retail Assistant — Main JS */

// ── Cart count refresh ──────────────────────────
async function refreshCartCount() {
  try {
    const res = await fetch('/api/cart');
    if (!res.ok) return;
    const data = await res.json();
    const el = document.getElementById('cartCount');
    if (el) el.textContent = (data.items || []).length;
  } catch (_) {}
}

// ── Add to cart via AJAX (optional progressive enhancement) ─
document.addEventListener('DOMContentLoaded', () => {
  refreshCartCount();

  // Navbar scroll effect
  const navbar = document.getElementById('mainNavbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 40);
    });
  }

  // Auto-dismiss alerts after 4 seconds
  document.querySelectorAll('.alert.lux-alert').forEach(el => {
    setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => el.remove(), 300);
    }, 4000);
  });

  // Product card image error fallback
  document.querySelectorAll('img[data-fallback]').forEach(img => {
    img.addEventListener('error', function () {
      this.src = this.dataset.fallback || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400';
    });
  });
});

// ── Chatbot toggle ──────────────────────────────
function toggleChatbot() {
  const win = document.getElementById('chatbotWindow');
  if (win) win.classList.toggle('open');
}

// ── Format currency ─────────────────────────────
function formatINR(amount) {
  return '₹' + Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2 });
}
