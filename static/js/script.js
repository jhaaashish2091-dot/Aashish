// Global variables for image navigation
let currentImageIndex = 0;
let allImages = [];

// Open Image Modal
function openImageModal(imgElement) {
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const caption = document.getElementById('modalCaption');
    
    // Get all images in the page
    allImages = Array.from(document.querySelectorAll('.post-img-clickable'));
    currentImageIndex = allImages.indexOf(imgElement);
    
    modal.classList.add('active');
    modalImg.src = imgElement.src;
    caption.textContent = imgElement.alt;
    
    // Prevent body scrolling when modal is open
    document.body.style.overflow = 'hidden';
}

// Close Image Modal
function closeImageModal() {
    const modal = document.getElementById('imageModal');
    modal.classList.remove('active');
    
    // Re-enable body scrolling
    document.body.style.overflow = 'auto';
}

// Navigate between images
function navigateImage(direction) {
    if (allImages.length === 0) return;
    
    currentImageIndex += direction;
    
    // Loop around
    if (currentImageIndex < 0) {
        currentImageIndex = allImages.length - 1;
    } else if (currentImageIndex >= allImages.length) {
        currentImageIndex = 0;
    }
    
    const modalImg = document.getElementById('modalImage');
    const caption = document.getElementById('modalCaption');
    
    modalImg.src = allImages[currentImageIndex].src;
    caption.textContent = allImages[currentImageIndex].alt;
}

// Close modal when clicking outside the image
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('imageModal');
    
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeImageModal();
            }
        });
    }
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        const modal = document.getElementById('imageModal');
        if (modal && modal.classList.contains('active')) {
            if (e.key === 'Escape') {
                closeImageModal();
            } else if (e.key === 'ArrowLeft') {
                navigateImage(-1);
            } else if (e.key === 'ArrowRight') {
                navigateImage(1);
            }
        }
    });

    // Image preview functionality for create/edit forms
    const imageInput = document.getElementById('image');
    const fileNameSpan = document.getElementById('file-name');
    const imagePreview = document.getElementById('image-preview');

    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            
            if (file) {
                // Update file name
                if (fileNameSpan) {
                    fileNameSpan.textContent = file.name;
                }

                // Show preview
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    
                    reader.onload = function(e) {
                        imagePreview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
                    };
                    
                    reader.readAsDataURL(file);
                } else {
                    imagePreview.innerHTML = '';
                }

                // Check file size
                const maxSize = 5 * 1024 * 1024; // 5MB
                if (file.size > maxSize) {
                    alert('File is too large! Maximum size is 5MB.');
                    imageInput.value = '';
                    fileNameSpan.textContent = 'No file chosen';
                    imagePreview.innerHTML = '';
                }
            } else {
                if (fileNameSpan) {
                    fileNameSpan.textContent = 'No file chosen';
                }
                imagePreview.innerHTML = '';
            }
        });
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Auto-hide flash messages
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('input[required], textarea[required]');
            let isValid = true;

            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.style.borderColor = '#ef4444';
                } else {
                    input.style.borderColor = '#e5e7eb';
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields');
            }
        });
    });

    // Character counter for textarea
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        const maxLength = 5000;
        const counter = document.createElement('div');
        counter.style.textAlign = 'right';
        counter.style.fontSize = '0.875rem';
        counter.style.color = '#6b7280';
        counter.style.marginTop = '0.5rem';
        
        textarea.parentNode.appendChild(counter);
        
        const updateCounter = () => {
            const remaining = maxLength - textarea.value.length;
            counter.textContent = `${textarea.value.length} / ${maxLength} characters`;
            
            if (remaining < 100) {
                counter.style.color = '#ef4444';
            } else {
                counter.style.color = '#6b7280';
            }
        };
        
        textarea.addEventListener('input', updateCounter);
        updateCounter();
    });

    // Animation for cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    document.querySelectorAll('.post-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.5s, transform 0.5s';
        observer.observe(card);
    });
});

// Add loading state to forms
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const submitBtn = this.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Loading...';
        }
    });
});