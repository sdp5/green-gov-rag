// Custom JavaScript for GreenGovRAG documentation

// Add smooth scroll behavior
document.addEventListener('DOMContentLoaded', function() {
  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href !== '#') {
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      }
    });
  });

  // Add copy success feedback
  document.querySelectorAll('.md-clipboard').forEach(button => {
    button.addEventListener('click', function() {
      const feedback = document.createElement('span');
      feedback.textContent = 'Copied!';
      feedback.style.cssText = 'position:absolute;right:0;top:-1.5rem;background:#2e7d32;color:white;padding:0.3rem 0.6rem;border-radius:4px;font-size:0.75rem;';
      this.style.position = 'relative';
      this.appendChild(feedback);
      setTimeout(() => feedback.remove(), 2000);
    });
  });
});
