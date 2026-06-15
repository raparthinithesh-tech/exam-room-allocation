// Examination Hall Allocation Portal

// ── Modal ──
function openModal(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.add('open');
  document.body.style.overflow = 'hidden';
  var first = el.querySelector('input:not([type=hidden]), select, textarea');
  if (first) setTimeout(function(){ first.focus(); }, 50);
}

function closeModal(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('open');
  document.body.style.overflow = '';
}

// Close on backdrop click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// Close on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(function(m) {
      m.classList.remove('open');
      document.body.style.overflow = '';
    });
  }
});

// ── Password show/hide ──
function togglePw(inputId, btn) {
  var input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = 'Hide';
  } else {
    input.type = 'password';
    btn.textContent = 'Show';
  }
}

// ── Allocation table search ──
function filterTable() {
  var val = document.getElementById('searchInput').value.toLowerCase();
  var rows = document.querySelectorAll('#allocTable tbody tr');
  rows.forEach(function(row) {
    row.style.display = row.textContent.toLowerCase().includes(val) ? '' : 'none';
  });
}

// ── Auto-dismiss alerts after 5s ──
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.alert-bar').forEach(function(el) {
    setTimeout(function() {
      el.style.transition = 'opacity .35s';
      el.style.opacity = '0';
      setTimeout(function() { el.remove(); }, 350);
    }, 5000);
  });
});
