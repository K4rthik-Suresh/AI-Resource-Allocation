// Initialize tooltips and popovers
document.addEventListener("DOMContentLoaded", () => {
  // Bootstrap tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  tooltipTriggerList.map((tooltipTriggerEl) => new window.bootstrap.Tooltip(tooltipTriggerEl))

  // Add loading state to forms -- SKIP rating forms (handled by AJAX handler below)
  document.querySelectorAll("form:not(.ajax-rating-form)").forEach((form) => {
    form.addEventListener("submit", function () {
      const submitBtn = this.querySelector('button[type="submit"]')
      if (submitBtn) {
        submitBtn.disabled = true
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...'
      }
    })
  })
})

// Utility functions
function formatDate(date) {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

function showNotification(message, type = "info") {
  const alertDiv = document.createElement("div")
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`
  alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `
  document.querySelector("main").prepend(alertDiv)
}

// ── Toast helper (real-time rating notifications) ─────────────────────────────
function showRatingToast(message, type) {
  const container = document.getElementById('rating-toast-container');
  if (!container) {
    // Fallback to old notification if toast container missing
    showNotification(message, type === 'success' ? 'success' : 'danger');
    return;
  }

  const id       = 'toast-' + Date.now();
  const bgClass  = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-warning';
  const txtClass = type === 'warning' ? 'text-dark' : 'text-white';
  const icon     = type === 'success' ? 'bi-check-circle-fill'
                 : type === 'error'   ? 'bi-x-circle-fill'
                 :                      'bi-exclamation-triangle-fill';

  container.insertAdjacentHTML('beforeend', `
    <div id="${id}"
         class="toast align-items-center ${txtClass} ${bgClass} border-0 mb-2 rating-toast"
         role="alert" aria-live="assertive" aria-atomic="true"
         data-bs-delay="3500">
      <div class="d-flex">
        <div class="toast-body">
          <i class="bi ${icon} me-2"></i>${message}
        </div>
        <button type="button"
                class="btn-close ${type !== 'warning' ? 'btn-close-white' : ''} me-2 m-auto"
                data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>`);

  const el    = document.getElementById(id);
  const toast = new bootstrap.Toast(el);
  toast.show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}

// ── AJAX Rating Form Handler ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const RATING_LABELS = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent'];

  // Star rating interactivity ─────────────────────────────────────────────────
  document.querySelectorAll('.star-rating-input').forEach(container => {
    const suffix  = container.id.replace('starRating', '');
    const labelEl = document.getElementById('ratingLabel' + suffix);
    container.querySelectorAll('input[type="radio"]').forEach(radio => {
      radio.addEventListener('change', function () {
        if (!labelEl) return;
        const val              = parseInt(this.value, 10);
        labelEl.textContent    = RATING_LABELS[val] + ' (' + val + '/5)';
        labelEl.style.color      = '#f59e0b';
        labelEl.style.fontWeight = '600';
      });
    });
  });

  // AJAX submission ───────────────────────────────────────────────────────────
  document.querySelectorAll('.ajax-rating-form').forEach(form => {
    form.addEventListener('submit', async function(e) {
      e.preventDefault();

      const submitBtn    = this.querySelector('button[type="submit"]');
      const originalHTML = submitBtn ? submitBtn.innerHTML : '';

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Submitting\u2026';
      }

      try {
        const formData = new FormData(this);
        const comment  = formData.get('comment') || '';

        const response = await fetch(this.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          }
        });

        const result = await response.json();

        // Close modal if form is inside one
        const modalEl = this.closest('.modal');
        if (modalEl) {
          const inst = bootstrap.Modal.getInstance(modalEl);
          if (inst) {
            inst.hide();
          } else {
            new bootstrap.Modal(modalEl).hide();
          }
          // Remove any lingering backdrop
          setTimeout(() => {
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow    = '';
            document.body.style.paddingRight = '';
          }, 350);
        }

        if (result.success) {
          showRatingToast(result.message, 'success');

          const bookingId = result.booking_id;
          const rating    = result.rating;

          // Update trigger button — id-based first, then data-attribute fallback
          let rateBtn = document.getElementById('ratingBtn' + bookingId);
          if (!rateBtn) {
            rateBtn = document.querySelector(`button[data-bs-target="#rateModal${bookingId}"]`);
          }
          if (rateBtn) {
            rateBtn.className = 'btn btn-sm btn-warning';
            rateBtn.innerHTML = `<i class="bi bi-star-fill"></i> ${rating}/5 <i class="bi bi-pencil-square ms-1" style="font-size:0.7rem;"></i>`;
            rateBtn.title     = `Edit your rating (${rating}/5)`;
          }

          // Detail-page live section refresh
          const detailSection = document.getElementById('rating-section-detail');
          if (detailSection) {
            const stars = Array.from({ length: 5 }, (_, i) => {
              const on = i < rating;
              return `<i class="bi bi-star${on ? '-fill' : ''}"
                         style="color:${on ? '#f59e0b' : '#d1d5db'};font-size:1.75rem;"></i>`;
            }).join('');

            const safeComment = comment
              ? `<div class="mt-3 p-3 bg-light rounded text-start">
                     <p class="small text-muted mb-1"><i class="bi bi-chat-left-text"></i> Your Comment</p>
                     <p class="mb-0">${comment.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
                 </div>`
              : '';

            const now = new Date().toLocaleDateString('en-US', {
              year: 'numeric', month: 'long', day: 'numeric'
            });

            detailSection.innerHTML = `
              <div class="text-center py-3 rating-detail-confirmed">
                <p class="text-muted mb-2">Your Rating</p>
                <div class="star-rating-display mb-2">${stars}</div>
                <p class="fw-bold mb-1" style="color:#f59e0b;">
                  ${rating}/5 \u2014 ${RATING_LABELS[rating]}
                </p>
                ${safeComment}
                <p class="text-muted small mt-2 mb-3">
                  <i class="bi bi-check-circle text-success"></i> Rated on ${now}
                </p>
                <button class="btn btn-sm btn-outline-warning" type="button"
                        data-bs-toggle="collapse" data-bs-target="#editRatingForm"
                        aria-expanded="false">
                  <i class="bi bi-pencil-square"></i> Edit Rating
                </button>
              </div>`;
          }

        } else {
          showRatingToast(result.message || 'Could not submit rating.', 'error');
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHTML;
          }
        }

      } catch (error) {
        console.error("Rating submission error:", error);
        showRatingToast("A network error occurred. Please try again.", 'error');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalHTML;
        }
      }
    });
  });
});
