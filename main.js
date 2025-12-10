// Main JavaScript file for Environmental Issues App

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add animation classes to elements
    addAnimationClasses();

    // Initialize smooth scrolling
    initSmoothScrolling();

    // Initialize form validation
    initFormValidation();

    // Initialize image preview functionality
    initImagePreview();

    // Initialize notification system
    initNotifications();

    // Initialize loading states
    initLoadingStates();
});

// Add animation classes to elements when they come into view
function addAnimationClasses() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);

    // Observe all cards and sections
    document.querySelectorAll('.card, .hero-section, section').forEach(el => {
        observer.observe(el);
    });
}

// Initialize smooth scrolling for anchor links
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Initialize form validation
function initFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
                form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Custom validation for file uploads
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            validateFileUpload(this);
        });
    });
}

// Validate file uploads
function validateFileUpload(input) {
    const files = input.files;
    const maxSize = 16 * 1024 * 1024; // 16MB
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    
    let isValid = true;
    let errorMessage = '';

    if (input.hasAttribute('multiple')) {
        if (files.length < 3 || files.length > 5) {
            isValid = false;
            errorMessage = 'Please select between 3 and 5 images.';
        }
    }

    Array.from(files).forEach(file => {
        if (!allowedTypes.includes(file.type)) {
            isValid = false;
            errorMessage = 'Please select only image files (JPG, PNG, GIF).';
        }
        if (file.size > maxSize) {
            isValid = false;
            errorMessage = 'File size should not exceed 16MB.';
        }
    });

    if (!isValid) {
        showNotification(errorMessage, 'error');
        input.value = '';
        clearImagePreview();
    }

    return isValid;
}

// Initialize image preview functionality
function initImagePreview() {
    const imageInput = document.getElementById('images');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            handleImagePreview(e.target.files);
        });
    }
}

// Handle image preview
function handleImagePreview(files) {
    const preview = document.getElementById('imagePreview');
    if (!preview) return;

    preview.innerHTML = '';

    if (files.length === 0) return;

    const row = document.createElement('div');
    row.className = 'row g-3 mt-2';

    Array.from(files).forEach((file, index) => {
        const col = document.createElement('div');
        col.className = 'col-md-4 col-sm-6';

        const reader = new FileReader();
        reader.onload = function(e) {
            col.innerHTML = `
                <div class="card">
                    <img src="${e.target.result}" 
                         class="card-img-top" 
                         style="height: 150px; object-fit: cover;"
                         alt="Preview ${index + 1}">
                    <div class="card-body p-2">
                        <small class="text-muted d-block">Image ${index + 1}</small>
                        <small class="text-muted">${formatFileSize(file.size)}</small>
                        <button type="button" 
                                class="btn btn-sm btn-outline-danger float-end"
                                onclick="removeImage(${index})">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        };
        reader.readAsDataURL(file);
        row.appendChild(col);
    });

    preview.appendChild(row);
}

// Clear image preview
function clearImagePreview() {
    const preview = document.getElementById('imagePreview');
    if (preview) {
        preview.innerHTML = '';
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Initialize notification system
function initNotifications() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (!alert.classList.contains('alert-permanent')) {
            setTimeout(() => {
                const alertInstance = new bootstrap.Alert(alert);
                alertInstance.close();
            }, 5000);
        }
    });
}

// Show notification
function showNotification(message, type = 'info', duration = 5000) {
    const alertTypes = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };

    const alertClass = alertTypes[type] || 'alert-info';
    const alertId = 'alert-' + Date.now();

    const alertHtml = `
        <div id="${alertId}" class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    // Find or create notification container
    let container = document.querySelector('.notification-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1060';
        document.body.appendChild(container);
    }

    container.insertAdjacentHTML('beforeend', alertHtml);

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const alertInstance = new bootstrap.Alert(alert);
                alertInstance.close();
            }
        }, duration);
    }
}

// Initialize loading states
function initLoadingStates() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                showLoadingState(submitBtn);
            }
        });
    });
}

// Show loading state on button
function showLoadingState(button) {
    const originalContent = button.innerHTML;
    const loadingText = button.getAttribute('data-loading-text') || 'Loading...';
    
    button.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${loadingText}`;
    button.disabled = true;

    // Store original content to restore later if needed
    button.setAttribute('data-original-content', originalContent);
}

// Hide loading state on button
function hideLoadingState(button) {
    const originalContent = button.getAttribute('data-original-content');
    if (originalContent) {
        button.innerHTML = originalContent;
        button.disabled = false;
    }
}

// Utility function to copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success', 2000);
    }).catch(() => {
        showNotification('Failed to copy to clipboard', 'error', 2000);
    });
}

// Utility function to confirm action
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Handle image modal gallery
function initImageGallery() {
    const imageModals = document.querySelectorAll('[data-bs-toggle="modal"]');
    imageModals.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.getAttribute('data-bs-target');
            const modal = document.querySelector(modalId);
            if (modal) {
                // Add any additional modal functionality here
                modal.addEventListener('shown.bs.modal', function() {
                    // Focus management or other modal enhancements
                });
            }
        });
    });
}

// Chart initialization (for dashboard)
function initCharts() {
    // Placeholder for chart initialization
    // You can integrate Chart.js or other charting libraries here
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach(container => {
        // Initialize charts based on data attributes or API calls
        console.log('Chart container found:', container);
    });
}

// Search functionality
function initSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(input => {
        input.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const targetSelector = this.getAttribute('data-target');
            const items = document.querySelectorAll(targetSelector);

            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

// Filter functionality
function initFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filterValue = this.getAttribute('data-filter');
            const targetSelector = this.getAttribute('data-target');
            const items = document.querySelectorAll(targetSelector);

            // Update active filter button
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // Filter items
            items.forEach(item => {
                if (filterValue === 'all' || item.classList.contains(filterValue)) {
                    item.style.display = '';
                    item.classList.add('fade-in');
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

// Lazy loading for images
function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.getAttribute('data-src');
                img.removeAttribute('data-src');
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => {
        imageObserver.observe(img);
    });
}

// Progress bar animation
function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    const progressObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const progressBar = entry.target;
                const width = progressBar.getAttribute('data-width');
                progressBar.style.width = width + '%';
            }
        });
    });

    progressBars.forEach(bar => {
        progressObserver.observe(bar);
    });
}

// Back to top button
function initBackToTop() {
    const backToTopBtn = document.createElement('button');
    backToTopBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
    backToTopBtn.className = 'btn btn-success btn-floating back-to-top';
    backToTopBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: none;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    `;

    document.body.appendChild(backToTopBtn);

    // Show/hide button based on scroll position
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            backToTopBtn.style.display = 'block';
        } else {
            backToTopBtn.style.display = 'none';
        }
    });

    // Scroll to top when clicked
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Initialize all components
function initAllComponents() {
    initImageGallery();
    initCharts();
    initSearch();
    initFilters();
    initLazyLoading();
    animateProgressBars();
    initBackToTop();
}

// Call initialization functions
setTimeout(initAllComponents, 1000);

// Export functions for global use
window.showNotification = showNotification;
window.confirmAction = confirmAction;
window.copyToClipboard = copyToClipboard;
window.showLoadingState = showLoadingState;
window.hideLoadingState = hideLoadingState;