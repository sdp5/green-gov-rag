// Custom JavaScript for GreenGovRAG documentation

// Fix for active menu items becoming invisible
// This ensures active navigation items remain visible even after mouse leaves
document.addEventListener('DOMContentLoaded', function() {
  // Force active state on navigation items (excluding right TOC sidebar)
  function maintainActiveStates() {
    // Fix active tabs (top navigation)
    const activeTabs = document.querySelectorAll('.md-tabs__link--active, .md-tabs__link[aria-current="page"]');
    activeTabs.forEach(tab => {
      tab.style.color = '#047857'; // var(--green-darker)
      tab.style.fontWeight = '600';
      tab.style.opacity = '1';
      tab.style.background = 'rgba(236, 253, 245, 0.5)';
    });

    // Fix active left sidebar navigation only (exclude right TOC sidebar)
    const activeSidebarLinks = document.querySelectorAll('.md-sidebar--primary .md-nav__link--active, .md-sidebar--primary .md-nav__link[aria-current="page"]');
    activeSidebarLinks.forEach(link => {
      link.style.color = '#059669'; // var(--green-dark)
      link.style.fontWeight = '600';
      link.style.borderLeftColor = '#10b981'; // var(--green-primary)
    });
  }

  // Run on load
  maintainActiveStates();

  // Re-run after navigation (Material theme uses XHR navigation)
  const observer = new MutationObserver(maintainActiveStates);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class', 'aria-current']
  });
});

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
