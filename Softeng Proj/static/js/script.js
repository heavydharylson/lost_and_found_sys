document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const foundButton = document.getElementById('foundButton');
    const itemContainer = document.getElementById('itemContainer');
    const uploadButton = document.getElementById('uploadButton');
    const categorySelect = document.getElementById('categorySelect');
    const fileInput = document.getElementById('fileInput');
    const uploadMessage = document.getElementById('uploadMessage');
    const compareButton = document.getElementById('compareButton');
    const compareFileInput = document.getElementById('compareFileInput');
    const compareCategorySelect = document.getElementById('compareCategorySelect');
    const compareMessage = document.getElementById('compareMessage');
    const compareResults = document.getElementById('compareResults');
    const showPassword = document.getElementById('showPassword');

    if (showPassword) {
        document.getElementById('showPassword').addEventListener('change', function() {
            const passwordField = document.getElementById('loginPassword');
            passwordField.type = this.checked ? 'text' : 'password';
        });
    }

    // Helper function to validate email
    function validateEmail(email) {
        const allowedDomains = ['cvsu.edu.ph', 'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'live.com', 'msn.com', 'icloud.com', 'yandex.com']; // List of allowed domains
        return allowedDomains.some(domain => email.endsWith(`@${domain}`));
    }


    // Register Form Submission
    if (registerForm) {
        registerForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const fullName = document.getElementById('registerName').value; // Add full name field
            const contactNumber = document.getElementById('registerNumber').value; // Add contact number field

            if (!validateEmail(email)) {
                document.getElementById('registerError').textContent = 'Please use a valid email address from an allowed domain (e.g., @gmail.com, @yahoo.com).';
                return;
            }

            // Send full data to the server including email, password, full name, and contact number
            fetch('http://localhost:5000/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, full_name: fullName, contact_no: contactNumber })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Registration successful! You can now log in.');
                    window.location.href = '/login';
                } else {
                    document.getElementById('registerError').textContent = data.message;
                }
            })
            .catch(() => {
                document.getElementById('registerError').textContent = 'Error connecting to server';
            });
        });
    }


    // Show the upload container when "Found" button is pressed
    foundButton.addEventListener('click', function () {
        itemContainer.style.display = 'block';
    });

    // Handle the file upload
    uploadButton.addEventListener('click', function () {
        const category = categorySelect.value;
        const file = fileInput.files[0];

        if (!category || !file) {
            uploadMessage.textContent = 'Please select a category and a file.';
            return;
        }

        const formData = new FormData();
        formData.append('category', category);
        formData.append('file', file);

        fetch('http://localhost:5000/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            uploadMessage.textContent = data.success ? 'File uploaded successfully!' : 'Error uploading file: ' + data.message;
        })
        .catch(() => {
            uploadMessage.textContent = 'Error connecting to server.';
        });
    });

    // Handle the image comparison
    if (compareButton) {
        compareButton.addEventListener('click', function () {
            const category = compareCategorySelect.value;
            const file = compareFileInput.files[0];

            if (!category || !file) {
                compareMessage.textContent = 'Please select a category and a file.';
                return;
            }

            const formData = new FormData();
            formData.append('image', file);
            formData.append('category', category);

            fetch('http://localhost:5000/compare', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                compareMessage.textContent = data.success ? 'Comparison successful!' : data.message || 'No matches found.';
                displayCompareResults(data.matches, data.low_matches);
            })
            .catch(() => {
                compareMessage.textContent = 'Error connecting to server.';
            });
        });
    }

    // Function to display comparison results
    function displayCompareResults(matches, lowMatches) {
        compareResults.innerHTML = ''; // Clear previous results

        if (matches && matches.length > 0) {
            const matchHeader = document.createElement('h3');
            matchHeader.textContent = 'Similar Images (50% or more)';
            compareResults.appendChild(matchHeader);

            matches.forEach(match => {
                const matchItem = document.createElement('div');
                matchItem.textContent = `File: ${match.filename}, Similarity: ${match.similarity.toFixed(2)}%`;
                compareResults.appendChild(matchItem);
            });
        }

        if (lowMatches && lowMatches.length > 0) {
            const lowMatchHeader = document.createElement('h3');
            lowMatchHeader.textContent = 'Low Similarity Images (Below 50%)';
            compareResults.appendChild(lowMatchHeader);

            lowMatches.forEach(lowMatch => {
                const lowMatchItem = document.createElement('div');
                lowMatchItem.textContent = `File: ${lowMatch.filename}, Similarity: ${lowMatch.similarity.toFixed(2)}%`;
                compareResults.appendChild(lowMatchItem);
            });
        }
    }
});
