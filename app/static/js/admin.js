// Dream & Drape Admin Panel JavaScript

$(document).ready(function() {
    // Initialize admin panel
    initializeAdminPanel();
    
    // Initialize components
    initializeDataTables();
    initializeCharts();
    initializeImageUploads();
    initializeFormValidations();
    initializeBulkActions();
    
    // Update stats periodically
    updateDashboardStats();
    setInterval(updateDashboardStats, 30000); // Every 30 seconds
});

// Initialize Admin Panel
function initializeAdminPanel() {
    // Sidebar toggle
    $('.sidebar-toggle').on('click', function() {
        $('.admin-sidebar').toggleClass('collapsed');
        $('.admin-content').toggleClass('expanded');
        
        // Save state to localStorage
        const isCollapsed = $('.admin-sidebar').hasClass('collapsed');
        localStorage.setItem('adminSidebarCollapsed', isCollapsed);
    });
    
    // Restore sidebar state
    const sidebarCollapsed = localStorage.getItem('adminSidebarCollapsed') === 'true';
    if (sidebarCollapsed) {
        $('.admin-sidebar').addClass('collapsed');
        $('.admin-content').addClass('expanded');
    }
    
    // Active nav link highlighting
    const currentPath = window.location.pathname;
    $('.admin-nav .nav-link').each(function() {
        const linkPath = $(this).attr('href');
        if (currentPath.includes(linkPath) && linkPath !== '/admin/') {
            $(this).addClass('active');
        } else if (currentPath === '/admin/' && linkPath === '/admin/') {
            $(this).addClass('active');
        }
    });
    
    // Mobile sidebar toggle
    if (window.innerWidth <= 576) {
        $('.admin-sidebar').removeClass('collapsed');
        $('.sidebar-toggle').on('click', function() {
            $('.admin-sidebar').toggleClass('show');
        });
        
        // Close sidebar when clicking outside
        $(document).on('click', function(e) {
            if (!$(e.target).closest('.admin-sidebar, .sidebar-toggle').length) {
                $('.admin-sidebar').removeClass('show');
            }
        });
    }
}

// Initialize Data Tables
function initializeDataTables() {
    // Enhanced data tables
    $('.admin-table').each(function() {
        const table = $(this);
        
        // Add sorting
        table.find('th').each(function(index) {
            if (!$(this).hasClass('no-sort')) {
                $(this).addClass('sortable').append(' <i class="fas fa-sort"></i>');
                $(this).on('click', function() {
                    sortTable(table, index, $(this));
                });
            }
        });
        
        // Add row selection
        if (table.hasClass('selectable')) {
            addRowSelection(table);
        }
    });
    
    // Search functionality
    $('.admin-search').on('input', function() {
        const searchTerm = $(this).val().toLowerCase();
        const targetTable = $($(this).data('target'));
        
        targetTable.find('tbody tr').each(function() {
            const rowText = $(this).text().toLowerCase();
            $(this).toggle(rowText.includes(searchTerm));
        });
        
        updateTableInfo(targetTable);
    });
}

// Sort Table
function sortTable(table, columnIndex, header) {
    const tbody = table.find('tbody');
    const rows = tbody.find('tr').toArray();
    const isAscending = !header.hasClass('sort-desc');
    
    // Reset all sort icons
    table.find('th i').removeClass('fa-sort-up fa-sort-down').addClass('fa-sort');
    
    // Set current sort icon
    const icon = header.find('i');
    icon.removeClass('fa-sort fa-sort-up fa-sort-down');
    if (isAscending) {
        icon.addClass('fa-sort-up');
        header.addClass('sort-asc').removeClass('sort-desc');
    } else {
        icon.addClass('fa-sort-down');
        header.addClass('sort-desc').removeClass('sort-asc');
    }
    
    rows.sort(function(a, b) {
        const aText = $(a).find('td').eq(columnIndex).text().trim();
        const bText = $(b).find('td').eq(columnIndex).text().trim();
        
        // Check if values are numbers
        const aNum = parseFloat(aText);
        const bNum = parseFloat(bText);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // String comparison
        return isAscending 
            ? aText.localeCompare(bText)
            : bText.localeCompare(aText);
    });
    
    tbody.empty().append(rows);
}

// Add Row Selection
function addRowSelection(table) {
    // Add header checkbox
    table.find('thead tr').prepend('<th class="no-sort"><input type="checkbox" id="selectAll"></th>');
    
    // Add row checkboxes
    table.find('tbody tr').each(function() {
        const rowId = $(this).data('id') || $(this).index();
        $(this).prepend(`<td><input type="checkbox" class="row-select" value="${rowId}"></td>`);
    });
    
    // Select all functionality
    $('#selectAll').on('change', function() {
        const isChecked = $(this).is(':checked');
        table.find('.row-select').prop('checked', isChecked);
        updateBulkActions();
    });
    
    // Individual row selection
    table.on('change', '.row-select', function() {
        const totalRows = table.find('.row-select').length;
        const selectedRows = table.find('.row-select:checked').length;
        
        $('#selectAll').prop('indeterminate', selectedRows > 0 && selectedRows < totalRows);
        $('#selectAll').prop('checked', selectedRows === totalRows);
        
        updateBulkActions();
    });
}

// Update Bulk Actions
function updateBulkActions() {
    const selectedCount = $('.row-select:checked').length;
    const bulkActions = $('.bulk-actions');
    
    if (selectedCount > 0) {
        bulkActions.show().find('.selected-count').text(selectedCount);
    } else {
        bulkActions.hide();
    }
}

// Initialize Bulk Actions
function initializeBulkActions() {
    // Bulk delete
    $('.bulk-delete').on('click', function() {
        const selectedIds = $('.row-select:checked').map(function() {
            return $(this).val();
        }).get();
        
        if (selectedIds.length === 0) {
            showAdminNotification('No items selected', 'warning');
            return;
        }
        
        if (confirm(`Delete ${selectedIds.length} selected items?`)) {
            performBulkAction('delete', selectedIds);
        }
    });
    
    // Bulk status change
    $('.bulk-status-change').on('click', function() {
        const selectedIds = $('.row-select:checked').map(function() {
            return $(this).val();
        }).get();
        
        if (selectedIds.length === 0) {
            showAdminNotification('No items selected', 'warning');
            return;
        }
        
        const newStatus = $(this).data('status');
        performBulkAction('status', selectedIds, { status: newStatus });
    });
}

// Perform Bulk Action
function performBulkAction(action, ids, data = {}) {
    showLoading();
    
    $.ajax({
        url: `/admin/bulk-action`,
        method: 'POST',
        data: {
            action: action,
            ids: ids,
            ...data
        },
        success: function(response) {
            hideLoading();
            if (response.success) {
                showAdminNotification(response.message, 'success');
                location.reload();
            } else {
                showAdminNotification(response.message, 'error');
            }
        },
        error: function() {
            hideLoading();
            showAdminNotification('Error performing bulk action', 'error');
        }
    });
}

// Initialize Charts
function initializeCharts() {
    // Sales Chart
    if ($('#salesChart').length) {
        createSalesChart();
    }
    
    // Orders Chart
    if ($('#ordersChart').length) {
        createOrdersChart();
    }
    
    // Category Distribution
    if ($('#categoryChart').length) {
        createCategoryChart();
    }
    
    // Revenue Chart
    if ($('#revenueChart').length) {
        createRevenueChart();
    }
}

// Create Sales Chart
function createSalesChart() {
    const ctx = document.getElementById('salesChart').getContext('2d');
    
    // Sample data - replace with actual data from API
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Sales',
                data: [12000, 15000, 13000, 17000, 16000, 19000],
                borderColor: '#f4c2c2',
                backgroundColor: 'rgba(244, 194, 194, 0.1)',
                borderWidth: 3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Create Orders Chart
function createOrdersChart() {
    const ctx = document.getElementById('ordersChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled'],
            datasets: [{
                data: [25, 45, 30, 120, 8],
                backgroundColor: [
                    '#f39c12',
                    '#3498db',
                    '#9b59b6',
                    '#27ae60',
                    '#e74c3c'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Create Category Chart
function createCategoryChart() {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Anarkali', 'Sarees', 'Kurtis', 'Lehenga'],
            datasets: [{
                label: 'Products',
                data: [45, 32, 28, 15],
                backgroundColor: [
                    '#f4c2c2',
                    '#d4af37',
                    '#3498db',
                    '#27ae60'
                ]
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create Revenue Chart
function createRevenueChart() {
    const ctx = document.getElementById('revenueChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Revenue',
                data: [3000, 2500, 4000, 3500, 5000, 7000, 6000],
                backgroundColor: 'rgba(212, 175, 55, 0.8)',
                borderColor: '#d4af37',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Initialize Image Uploads
function initializeImageUploads() {
    // File upload preview
    $('.image-upload').on('change', function() {
        const file = this.files[0];
        const preview = $(this).siblings('.image-upload-preview');
        
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.html(`<img src="${e.target.result}" alt="Preview">`);
            };
            reader.readAsDataURL(file);
        }
    });
    
    // Drag and drop upload
    $('.image-upload-preview').on('dragover', function(e) {
        e.preventDefault();
        $(this).addClass('drag-over');
    });
    
    $('.image-upload-preview').on('dragleave', function(e) {
        e.preventDefault();
        $(this).removeClass('drag-over');
    });
    
    $('.image-upload-preview').on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('drag-over');
        
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            const fileInput = $(this).siblings('.image-upload')[0];
            fileInput.files = files;
            $(fileInput).trigger('change');
        }
    });
    
    // Click to upload
    $('.image-upload-preview').on('click', function() {
        $(this).siblings('.image-upload').click();
    });
}

// Initialize Form Validations
function initializeFormValidations() {
    // Admin form validation
    $('.admin-form').on('submit', function(e) {
        e.preventDefault();
        
        const form = $(this);
        let isValid = true;
        
        // Reset previous validation
        form.find('.is-invalid').removeClass('is-invalid');
        form.find('.invalid-feedback').hide();
        
        // Required field validation
        form.find('[required]').each(function() {
            const field = $(this);
            const value = field.val().trim();
            
            if (!value) {
                field.addClass('is-invalid');
                field.siblings('.invalid-feedback').show();
                isValid = false;
            }
        });
        
        // Email validation
        form.find('input[type="email"]').each(function() {
            const email = $(this).val().trim();
            if (email && !isValidEmail(email)) {
                $(this).addClass('is-invalid');
                $(this).siblings('.invalid-feedback').text('Invalid email format').show();
                isValid = false;
            }
        });
        
        // Price validation
        form.find('.price-input').each(function() {
            const price = parseFloat($(this).val());
            if (isNaN(price) || price < 0) {
                $(this).addClass('is-invalid');
                $(this).siblings('.invalid-feedback').text('Invalid price').show();
                isValid = false;
            }
        });
        
        if (isValid) {
            submitAdminForm(form);
        } else {
            showAdminNotification('Please fix the form errors', 'error');
        }
    });
    
    // Real-time validation
    $('.admin-form input, .admin-form textarea, .admin-form select').on('blur', function() {
        validateField($(this));
    });
}

// Validate Individual Field
function validateField(field) {
    const value = field.val().trim();
    
    // Remove previous validation
    field.removeClass('is-invalid is-valid');
    field.siblings('.invalid-feedback').hide();
    
    // Required validation
    if (field.prop('required') && !value) {
        field.addClass('is-invalid');
        field.siblings('.invalid-feedback').text('This field is required').show();
        return false;
    }
    
    // Email validation
    if (field.attr('type') === 'email' && value && !isValidEmail(value)) {
        field.addClass('is-invalid');
        field.siblings('.invalid-feedback').text('Invalid email format').show();
        return false;
    }
    
    // Number validation
    if (field.attr('type') === 'number' && value) {
        const num = parseFloat(value);
        const min = parseFloat(field.attr('min'));
        const max = parseFloat(field.attr('max'));
        
        if (isNaN(num)) {
            field.addClass('is-invalid');
            field.siblings('.invalid-feedback').text('Invalid number').show();
            return false;
        }
        
        if (!isNaN(min) && num < min) {
            field.addClass('is-invalid');
            field.siblings('.invalid-feedback').text(`Minimum value is ${min}`).show();
            return false;
        }
        
        if (!isNaN(max) && num > max) {
            field.addClass('is-invalid');
            field.siblings('.invalid-feedback').text(`Maximum value is ${max}`).show();
            return false;
        }
    }
    
    if (value) {
        field.addClass('is-valid');
    }
    
    return true;
}

// Submit Admin Form
function submitAdminForm(form) {
    const formData = new FormData(form[0]);
    const url = form.attr('action') || window.location.pathname;
    const method = form.attr('method') || 'POST';
    
    showLoading();
    
    $.ajax({
        url: url,
        method: method,
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            hideLoading();
            
            if (response.success) {
                showAdminNotification(response.message, 'success');
                
                // Redirect if specified
                if (response.redirect) {
                    setTimeout(() => {
                        window.location.href = response.redirect;
                    }, 1500);
                }
            } else {
                showAdminNotification(response.message || 'Form submission failed', 'error');
                
                // Show field-specific errors
                if (response.errors) {
                    Object.keys(response.errors).forEach(field => {
                        const fieldElement = form.find(`[name="${field}"]`);
                        fieldElement.addClass('is-invalid');
                        fieldElement.siblings('.invalid-feedback').text(response.errors[field]).show();
                    });
                }
            }
        },
        error: function(xhr) {
            hideLoading();
            const errorMessage = xhr.responseJSON?.message || 'Form submission failed';
            showAdminNotification(errorMessage, 'error');
        }
    });
}

// Update Dashboard Stats
function updateDashboardStats() {
    if (!$('.admin-stats').length) return;
    
    $.ajax({
        url: '/admin/api/stats',
        method: 'GET',
        success: function(stats) {
            // Update stat cards
            $('.admin-stat-card[data-stat="products"] .stat-number').text(stats.total_products || 0);
            $('.admin-stat-card[data-stat="users"] .stat-number').text(stats.total_users || 0);
            $('.admin-stat-card[data-stat="orders"] .stat-number').text(stats.total_orders || 0);
            $('.admin-stat-card[data-stat="revenue"] .stat-number').text('₹' + (stats.total_revenue || 0).toLocaleString());
            
            // Update badges
            $('.admin-nav .badge').each(function() {
                const type = $(this).data('type');
                if (stats[type]) {
                    $(this).text(stats[type]).show();
                } else {
                    $(this).hide();
                }
            });
        },
        error: function() {
            console.log('Failed to update dashboard stats');
        }
    });
}

// Admin Notifications
function showAdminNotification(message, type = 'info', duration = 5000) {
    const alertClass = type === 'error' ? 'danger' : type;
    const notification = $(`
        <div class="admin-alert ${alertClass} alert-dismissible fade show" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('body').append(notification);
    
    // Auto remove
    //setTimeout(() => {
        //notification.fadeOut(() => {
            //notification.remove();
        //});
    //}, duration); //
}

// Loading States
function showLoading() {
    const loader = $(`
        <div class="admin-loading-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;">
            <div class="admin-spinner"></div>
        </div>
    `);
    
    $('body').append(loader);
}

function hideLoading() {
    $('.admin-loading-overlay').remove();
}

// Modal Management
function showAdminModal(title, content, actions = []) {
    const modal = $(`
        <div class="modal fade admin-modal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${content}
                    </div>
                    <div class="modal-footer">
                        ${actions.map(action => `<button type="button" class="btn btn-${action.type}" onclick="${action.action}">${action.label}</button>`).join('')}
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `);
    
    $('body').append(modal);
    modal.modal('show');
    
    modal.on('hidden.bs.modal', function() {
        modal.remove();
    });
    
    return modal;
}

// Confirm Dialog
function confirmAction(message, callback) {
    const modal = showAdminModal(
        'Confirm Action',
        `<p>${message}</p>`,
        [
            {
                label: 'Confirm',
                type: 'danger',
                action: `confirmCallback(); $('.admin-modal').modal('hide');`
            }
        ]
    );
    
    window.confirmCallback = callback;
}

// Quick Actions
function quickAddProduct() {
    window.location.href = '/admin/product/add';
}

function quickAddCategory() {
    window.location.href = '/admin/category/add';
}

function viewRecentOrders() {
    window.location.href = '/admin/orders';
}

function viewPendingReviews() {
    window.location.href = '/admin/reviews?status=pending';
}

// Export Functions
function exportData(type, format = 'csv') {
    showLoading();
    
    $.ajax({
        url: `/admin/export/${type}`,
        method: 'POST',
        data: { format: format },
        success: function(response) {
            hideLoading();
            
            if (response.success) {
                // Create download link
                const link = document.createElement('a');
                link.href = response.download_url;
                link.download = response.filename;
                link.click();
                
                showAdminNotification('Export completed successfully', 'success');
            } else {
                showAdminNotification(response.message, 'error');
            }
        },
        error: function() {
            hideLoading();
            showAdminNotification('Export failed', 'error');
        }
    });
}

// Search Enhancement
function initializeAdvancedSearch() {
    $('.admin-advanced-search').on('click', function() {
        $('.admin-search-filters').slideToggle();
    });
    
    $('.admin-search-filters form').on('submit', function(e) {
        e.preventDefault();
        
        const filters = {};
        $(this).find('input, select').each(function() {
            const name = $(this).attr('name');
            const value = $(this).val();
            if (value) {
                filters[name] = value;
            }
        });
        
        applyFilters(filters);
    });
}

// Apply Filters
function applyFilters(filters) {
    const params = new URLSearchParams(filters);
    window.location.href = `${window.location.pathname}?${params.toString()}`;
}

// Update Table Info
function updateTableInfo(table) {
    const totalRows = table.find('tbody tr').length;
    const visibleRows = table.find('tbody tr:visible').length;
    
    table.siblings('.table-info').text(`Showing ${visibleRows} of ${totalRows} entries`);
}

// Utility Functions
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function formatCurrency(amount) {
    return '₹' + amount.toLocaleString('en-IN');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN');
}

// Auto-save functionality
function initializeAutoSave() {
    let autoSaveTimer;
    
    $('.admin-form input, .admin-form textarea').on('input', function() {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            autoSaveForm($(this).closest('.admin-form'));
        }, 2000);
    });
}

function autoSaveForm(form) {
    const formData = new FormData(form[0]);
    formData.append('auto_save', '1');
    
    $.ajax({
        url: form.attr('action') || window.location.pathname,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                showAdminNotification('Auto-saved', 'info', 1000);
            }
        }
    });
}

// Initialize on page load
$(window).on('load', function() {
    // Initialize additional features
    initializeAdvancedSearch();
    initializeAutoSave();
    
    // Remove loading states
    $('.admin-loading').fadeOut();
});

// Handle window resize
$(window).on('resize', function() {
    // Responsive adjustments
    if (window.innerWidth <= 768) {
        $('.admin-sidebar').addClass('collapsed');
        $('.admin-content').addClass('expanded');
    }
});

$(document).ready(function() {
    // Initialize charts with empty data first
    const salesCtx = document.getElementById('salesChart').getContext('2d');
    const ordersCtx = document.getElementById('ordersChart').getContext('2d');
    const categoryCtx = document.getElementById('categoryChart').getContext('2d');
    const revenueCtx = document.getElementById('revenueChart').getContext('2d');

    const salesChart = new Chart(salesCtx, {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Sales', data: [], borderColor: '#ffc0cb', fill: false }] },
        options: { responsive: true, aspectRatio: 2 }
    });

    const ordersChart = new Chart(ordersCtx, {
        type: 'doughnut',
        data: {
            labels: ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled'],
            datasets: [{ data: [], backgroundColor: ['#FFA500','#2196f3','#9c27b0','#4caf50','#f44336'] }]
        },
        options: { responsive: true, aspectRatio:1 }
    });

    const categoryChart = new Chart(categoryCtx, {
        type: 'bar',
        data: { labels: [], datasets: [{ label: 'Products', data: [], backgroundColor: '#ffc0cb' }] },
        options: { responsive: true, aspectRatio: 1.5 }
    });

    const revenueChart = new Chart(revenueCtx, {
        type: 'bar',
        data: { labels: [], datasets: [{ label: 'Revenue', data: [], backgroundColor: '#d4af37' }] },
        options: { responsive: true, aspectRatio:1.5 }
    });

    // Fetch data and update sales chart
    $.getJSON('/admin/api/sales_overview', function(data) {
        salesChart.data.labels = data.labels;
        salesChart.data.datasets[0].data = data.totals;
        salesChart.update();
    });

    // Fetch data and update orders chart
    $.getJSON('/admin/api/order_status', function(data) {
        ordersChart.data.datasets[0].data = [
            data.pending,
            data.confirmed,
            data.shipped,
            data.delivered,
            data.cancelled
        ];
        ordersChart.update();
    });

    // Fetch data and update product categories chart
    $.getJSON('/admin/api/product_categories', function(data) {
        categoryChart.data.labels = data.labels;
        categoryChart.data.datasets[0].data = data.counts;
        categoryChart.update();
    });

    // Fetch data and update weekly revenue chart
    $.getJSON('/admin/api/weekly_revenue', function(data) {
        revenueChart.data.labels = data.labels;
        revenueChart.data.datasets[0].data = data.totals;
        revenueChart.update();
    });
});
