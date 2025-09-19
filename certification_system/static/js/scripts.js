// Toggle sidebar
$("#menu-toggle").click(function(e) {
    e.preventDefault();
    $("#wrapper").toggleClass("toggled");
});

// Select all functionality
$('#selectAll').click(function() {
    $('.student-checkbox').prop('checked', this.checked);
    updateSelectedCount();
});

// Update selected count
function updateSelectedCount() {
    const selectedCount = $('.student-checkbox:checked').length;
    $('#selectedCount').text(selectedCount);
    $('#sendSelected, #deleteSelected').prop('disabled', selectedCount === 0);
}

// Initialize DataTable with search and pagination
$(document).ready(function() {
    $('.data-table').DataTable({
        "pageLength": 10,
        "lengthMenu": [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]]
    });
});


// CSRF token setup for AJAX
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Set CSRF token for all AJAX requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});