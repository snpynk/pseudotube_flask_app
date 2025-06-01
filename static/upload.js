document.addEventListener('DOMContentLoaded', function () {
	const uploadButton = document.getElementById("upload-button");
	const modal = document.querySelector('.modal-overlay');
	const closeButton = document.getElementById("upload-modal-close-button");

	if (uploadButton && modal && closeButton) {
		uploadButton.addEventListener('click', () => modal.classList.add('active'));
		closeButton.addEventListener('click', () => modal.classList.remove('active'));

		modal.addEventListener('click', (e) => {
			if (e.target === modal) modal.classList.remove('active');
		});

		const uploadArea = document.querySelector('.upload-area');
		const fileInput = document.getElementById('file-upload');
		const uploadText = document.getElementById('upload-text');

		uploadArea.addEventListener('dragover', (e) => {
			e.preventDefault();
			uploadArea.classList.add('dragging');
		});

		uploadArea.addEventListener('dragleave', () => {
			uploadArea.classList.remove('dragging');
		});

		uploadArea.addEventListener('drop', (e) => {
			e.preventDefault();
			uploadArea.classList.remove('dragging');
			fileInput.files = e.dataTransfer.files;
			uploadText.textContent = e.dataTransfer.files[0].name;
		});

		fileInput.addEventListener('change', () => {
			if (fileInput.files.length > 0) {
				uploadText.textContent = fileInput.files[0].name;
			} else {
				uploadText.textContent = 'Click or drag file here to upload';
			}
		});
	}

	const form = document.querySelector('.upload-form');
	const progressBar = document.getElementById('upload-progress');
	const statusText = document.getElementById('upload-status');

	if (form) {
		form.addEventListener('submit', function (e) {
			e.preventDefault();

			const formData = new FormData(form);

			const xhr = new XMLHttpRequest();
			xhr.open('POST', form.action, true);

			progressBar.style.display = 'block';
			statusText.textContent = 'Uploading...';

			xhr.upload.onprogress = function (e) {
				if (e.lengthComputable) {
					const percent = (e.loaded / e.total) * 100;
					progressBar.value = percent;
					statusText.textContent = `Uploading... ${Math.round(percent)}%`;
				}
			};

			xhr.onload = function () {
				if (xhr.status === 200) {
					progressBar.value = 100;
					statusText.textContent = 'Upload complete! Redirecting...';

					const response = JSON.parse(xhr.responseText);
					if (response.redirect_url) {
						setTimeout(() => {
							window.location.href = response.redirect_url;
						}, 1000);
					}
				} else {
					statusText.textContent = 'Upload failed. Please try again.';
				}
			};

			xhr.onerror = function () {
				statusText.textContent = 'An error occurred during upload.';
			};

			xhr.send(formData);
		});
	}
});
