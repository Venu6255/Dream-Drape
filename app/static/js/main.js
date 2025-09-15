// Dream & Drape - Main JavaScript

$(document).ready(function() {
    // Initialize components
    initializeComponents();
    
    // Update cart count on page load
    updateCartCount();
    
    // Auto-hide alerts
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

function initializeComponents() {
    // Product image gallery
    initializeImageGallery();
    
    // Quantity controls
    initializeQuantityControls();
    
    // Search functionality
    initializeSearch();
    
    // Form validations
    initializeFormValidations();
    
    // Smooth scrolling
    initializeSmoothScrolling();
}

// Product Image Gallery
function initializeImageGallery() {
    $('.thumbnail').click(function() {
        var newSrc = $(this).attr('src');
        $('.main-image').attr('src', newSrc);
        $('.thumbnail').removeClass('active');
        $(this).addClass('active');
    });
}

// Quantity Controls
function initializeQuantityControls() {
    // Increase quantity
    $(document).on('click', '.quantity-increase', function() {
        var input = $(this).siblings('.quantity-input');
        var currentVal = parseInt(input.val()) || 1;
        var maxVal = parseInt(input.attr('max')) || 10;
        
        if (currentVal < maxVal) {
            input.val(currentVal + 1).trigger('change');
        }
    });
    
    // Decrease quantity
    $(document).on('click', '.quantity-decrease', function() {
        var input = $(this).siblings('.quantity-input');
        var currentVal = parseInt(input.val()) || 1;
        var minVal = parseInt(input.attr('min')) || 1;
        
        if (currentVal > minVal) {
            input.val(currentVal - 1).trigger('change');
        }
    });
    
    // Direct input validation
    $(document).on('change', '.quantity-input', function() {
        var value = parseInt($(this).val());
        var min = parseInt($(this).attr('min')) || 1;
        var max = parseInt($(this).attr('max')) || 10;
        
        if (isNaN(value) || value < min) {
            $(this).val(min);
        } else if (value > max) {
            $(this).val(max);
        }
    });
}

// Search Functionality
function initializeSearch() {
    var searchInput = $('input[name="search"]');
    var searchTimeout;
    
    searchInput.on('input', function() {
        var query = $(this).val();
        
        // Clear previous timeout
        clearTimeout(searchTimeout);
        
        // Set new timeout for search suggestions
        if (query.length >= 2) {
            searchTimeout = setTimeout(function() {
                getSearchSuggestions(query);
            }, 300);
        } else {
            hideSearchSuggestions();
        }
    });
    
    // Hide suggestions when clicking outside
    $(document).click(function(e) {
        if (!$(e.target).closest('.search-container').length) {
            hideSearchSuggestions();
        }
    });
}

function getSearchSuggestions(query) {
    $.ajax({
        url: '/api/search_suggestions',
        method: 'GET',
        data: { q: query },
        success: function(suggestions) {
            displaySearchSuggestions(suggestions);
        },
        error: function() {
            console.log('Error fetching search suggestions');
        }
    });
}

function displaySearchSuggestions(suggestions) {
    var suggestionsHtml = '';
    
    if (suggestions.length > 0) {
        suggestionsHtml = '<div class="search-suggestions">';
        suggestions.forEach(function(item) {
            suggestionsHtml += '<div class="search-suggestion-item" onclick="selectSearchSuggestion(\'' + item.name + '\')">';
            suggestionsHtml += '<span class="suggestion-name">' + item.name + '</span>';
            suggestionsHtml += '<span class="suggestion-price">₹' + item.price.toFixed(2) + '</span>';
            suggestionsHtml += '</div>';
        });
        suggestionsHtml += '</div>';
    }
    
    // Remove existing suggestions
    $('.search-suggestions').remove();
    
    // Add new suggestions
    if (suggestionsHtml) {
        $('input[name="search"]').parent().append(suggestionsHtml);
    }
}

function selectSearchSuggestion(productName) {
    $('input[name="search"]').val(productName);
    hideSearchSuggestions();
    $('input[name="search"]').closest('form').submit();
}

function hideSearchSuggestions() {
    $('.search-suggestions').remove();
}

// Cart Functions
function updateCartCount() {
    $.ajax({
        url: '/api/cart_count',
        method: 'GET',
        success: function(data) {
            $('#cart-count').text(data.count);
            if (data.count > 0) {
                $('#cart-count').show();
            } else {
                $('#cart-count').hide();
            }
        },
        error: function() {
            console.log('Error updating cart count');
        }
    });
}

function addToCart(productId, quantity, size, color) {
    var formData = new FormData();
    formData.append('product_id', productId);
    formData.append('quantity', quantity || 1);
    formData.append('size', size || '');
    formData.append('color', color || '');
    
    $.ajax({
        url: '/add_to_cart',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            showNotification('Product added to cart!', 'success');
            updateCartCount();
        },
        error: function() {
            showNotification('Error adding product to cart!', 'error');
        }
    });
}

function removeFromCart(itemId) {
    if (confirm('Are you sure you want to remove this item from your cart?')) {
        window.location.href = '/remove_from_cart/' + itemId;
    }
}

function updateCartItem(itemId, quantity) {
    var form = $('<form>', {
        method: 'POST',
        action: '/update_cart'
    });
    
    form.append($('<input>', {
        type: 'hidden',
        name: 'item_id',
        value: itemId
    }));
    
    form.append($('<input>', {
        type: 'hidden',
        name: 'quantity',
        value: quantity
    }));
    
    $('body').append(form);
    form.submit();
}

// Wishlist Functions
function toggleWishlist(productId) {
    $.ajax({
        url: '/add_to_wishlist/' + productId,
        method: 'GET',
        success: function() {
            // Toggle wishlist button appearance
            var btn = $('button[onclick="toggleWishlist(' + productId + ')"]');
            btn.toggleClass('active');
            
            if (btn.hasClass('active')) {
                showNotification('Added to wishlist!', 'success');
            } else {
                showNotification('Removed from wishlist!', 'info');
            }
        },
        error: function() {
            showNotification('Please login to add items to wishlist!', 'error');
            setTimeout(function() {
                window.location.href = '/auth/login';
            }, 2000);
        }
    });
}

function removeFromWishlist(productId) {
    if (confirm('Remove this item from your wishlist?')) {
        window.location.href = '/remove_from_wishlist/' + productId;
    }
}

// Size and Color Selection
function selectSize(element, size) {
    $('.size-option').removeClass('active');
    $(element).addClass('active');
    $('select[name="size"]').val(size);
}

function selectColor(element, color) {
    $('.color-option').removeClass('active');
    $(element).addClass('active');
    $('select[name="color"]').val(color);
}

// Form Validations
function initializeFormValidations() {
    // Bootstrap form validation
    (function() {
        'use strict';
        window.addEventListener('load', function() {
            var forms = document.getElementsByClassName('needs-validation');
            var validation = Array.prototype.filter.call(forms, function(form) {
                form.addEventListener('submit', function(event) {
                    if (form.checkValidity() === false) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                    form.classList.add('was-validated');
                }, false);
            });
        }, false);
    })();
    
    // Password confirmation validation
    $('input[name="password2"]').on('input', function() {
        var password = $('input[name="password"]').val();
        var confirmPassword = $(this).val();
        
        if (password !== confirmPassword) {
            this.setCustomValidity('Passwords do not match');
        } else {
            this.setCustomValidity('');
        }
    });
}

// Smooth Scrolling
function initializeSmoothScrolling() {
    $('a[href*="#"]:not([href="#"])').click(function() {
        if (location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '') && location.hostname == this.hostname) {
            var target = $(this.hash);
            target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
            if (target.length) {
                $('html, body').animate({
                    scrollTop: target.offset().top - 80
                }, 1000);
                return false;
            }
        }
    });
}

// Notification System
function showNotification(message, type) {
    type = type || 'info';
    var alertClass = 'alert-' + (type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info');
    
    var notification = $('<div>', {
        class: 'alert ' + alertClass + ' alert-dismissible fade show position-fixed',
        style: 'top: 100px; right: 20px; z-index: 9999; min-width: 300px;',
        html: message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'
    });
    
    $('body').append(notification);
    
    // Auto remove after 5 seconds
    setTimeout(function() {
        notification.fadeOut(function() {
            $(this).remove();
        });
    }, 5000);
}

// Price Filter
function updatePriceRange() {
    var minPrice = $('#min-price').val();
    var maxPrice = $('#max-price').val();
    var url = new URL(window.location);
    
    if (minPrice) {
        url.searchParams.set('min_price', minPrice);
    } else {
        url.searchParams.delete('min_price');
    }
    
    if (maxPrice) {
        url.searchParams.set('max_price', maxPrice);
    } else {
        url.searchParams.delete('max_price');
    }
    
    window.location.href = url.toString();
}

// Loading States
function showLoading(element) {
    var loadingHtml = '<span class="loading me-2"></span>Loading...';
    $(element).html(loadingHtml).prop('disabled', true);
}

function hideLoading(element, originalText) {
    $(element).html(originalText).prop('disabled', false);
}

// Image Lazy Loading
function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        const lazyImages = document.querySelectorAll('img[data-src]');
        lazyImages.forEach(img => imageObserver.observe(img));
    }
}

// Review Functions
function submitReview(productId) {
    var rating = $('select[name="rating"]').val();
    var comment = $('textarea[name="comment"]').val();
    
    if (!rating || !comment.trim()) {
        showNotification('Please provide both rating and comment', 'error');
        return;
    }
    
    var form = $('#review-form');
    form.submit();
}

// Newsletter
function subscribeNewsletter() {
    var email = $('input[name="email"]').val();
    
    if (!email || !isValidEmail(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    $.ajax({
        url: '/newsletter_signup',
        method: 'POST',
        data: { email: email },
        success: function() {
            showNotification('Thank you for subscribing!', 'success');
            $('input[name="email"]').val('');
        },
        error: function() {
            showNotification('Error subscribing to newsletter', 'error');
        }
    });
}

function isValidEmail(email) {
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Keyboard shortcuts
$(document).keydown(function(e) {
    // Ctrl+K or Cmd+K for search
    if ((e.ctrlKey || e.metaKey) && e.keyCode === 75) {
        e.preventDefault();
        $('input[name="search"]').focus();
    }
    
    // ESC to close modals/suggestions
    if (e.keyCode === 27) {
        hideSearchSuggestions();
        $('.modal').modal('hide');
    }
});

// Product Quick View
function quickView(productId) {
    // Load product details in modal
    $.ajax({
        url: '/product/' + productId,
        method: 'GET',
        success: function(data) {
            // Create and show modal with product data
            var modal = createQuickViewModal(data);
            $(modal).modal('show');
        },
        error: function() {
            showNotification('Error loading product details', 'error');
        }
    });
}

function createQuickViewModal(productData) {
    // Create modal HTML structure for quick view
    var modalHtml = '<div class="modal fade" id="quickViewModal" tabindex="-1">';
    modalHtml += '<div class="modal-dialog modal-lg">';
    modalHtml += '<div class="modal-content">';
    modalHtml += '<div class="modal-header">';
    modalHtml += '<h5 class="modal-title">Quick View</h5>';
    modalHtml += '<button type="button" class="btn-close" data-bs-dismiss="modal"></button>';
    modalHtml += '</div>';
    modalHtml += '<div class="modal-body">';
    modalHtml += productData; // Simplified - would need proper parsing
    modalHtml += '</div>';
    modalHtml += '</div>';
    modalHtml += '</div>';
    modalHtml += '</div>';
    
    // Remove existing modal if any
    $('#quickViewModal').remove();
    
    // Add new modal to body
    $('body').append(modalHtml);
    
    return '#quickViewModal';
}

// Checkout Form Enhancement
function validateCheckoutForm() {
    var isValid = true;
    var requiredFields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'pincode'];
    
    requiredFields.forEach(function(field) {
        var value = $('input[name="' + field + '"], textarea[name="' + field + '"]').val();
        if (!value || !value.trim()) {
            showNotification('Please fill in all required fields', 'error');
            isValid = false;
            return false;
        }
    });
    
    // Email validation
    var email = $('input[name="email"]').val();
    if (!isValidEmail(email)) {
        showNotification('Please enter a valid email address', 'error');
        isValid = false;
    }
    
    // Phone validation
    var phone = $('input[name="phone"]').val();
    if (phone && !/^[0-9]{10}$/.test(phone.replace(/\s+/g, ''))) {
        showNotification('Please enter a valid 10-digit phone number', 'error');
        isValid = false;
    }
    
    return isValid;
}

// Initialize everything when document is ready
$(document).ready(function() {
    initializeLazyLoading();
});