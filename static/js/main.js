document.addEventListener('DOMContentLoaded', function() {
    console.log('DataTrust AI: Application Initialized');

    // 1. File Upload Interaction
    const fileInput = document.getElementById('inputGroupFile02');
    const uploadWrapper = document.querySelector('.file-upload-wrapper');
    const uploadText = document.getElementById('uploadText');

    if (fileInput && uploadWrapper) {
        fileInput.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name || 'No file selected';
            if (uploadText) {
                uploadText.textContent = `Selected: ${fileName}`;
                uploadWrapper.style.borderColor = '#1cc88a'; // Change to success color
                uploadWrapper.style.backgroundColor = '#f8f9fc';
            }
        });

        // 2. Drag & Drop Visuals
        uploadWrapper.addEventListener('dragover', () => {
            uploadWrapper.style.borderColor = '#4e73df';
            uploadWrapper.style.backgroundColor = '#eaecf4';
        });

        uploadWrapper.addEventListener('dragleave', () => {
            uploadWrapper.style.borderColor = '#d1d3e2';
            uploadWrapper.style.backgroundColor = '#ffffff';
        });
    }

    // 3. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // 4. Smooth scroll for internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // 5. Loading states on form submission
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
                submitBtn.disabled = true;
            }
        });
    });

    // 6. Tooltip Initialization
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
