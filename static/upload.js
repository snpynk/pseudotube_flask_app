// the upload process changed
// when the modal is opened, an HTTP request should be made to fetch the file upload URL
// the file should be uploaded to that URL
// once the upload is complete, the user should send a POST request to a certain endpoint  with the file URL and hash
//
document.addEventListener('DOMContentLoaded', function () {
	const uploadButton = document.getElementById("upload-button");
	const modal = document.querySelector('.modal-overlay');
	const closeButton = document.getElementById("upload-modal-close-button");

	const data = {
		upload_url: '',
		upload_hash: '',
	};

	if (uploadButton && modal && closeButton) {
		uploadButton.addEventListener('click', () => {
			fetch("/upload", { method: 'GET' })
				.then(response => response.json())
				.then(response_data => {
					if (response_data.upload_url) {
						data.upload_url = response_data.upload_url;
						data.upload_hash = response_data.upload_hash;
						document.getElementById('upload-form').action = data.upload_url;
					} else {
						alert('Failed to get upload URL. Please try again later.');
					}

					modal.classList.add('active')
				})
				.catch(error => {
					console.error('Error fetching upload URL:', error);
					alert('An error occurred while trying to get the upload URL.');
				});
		});

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

	const form = document.getElementById('upload-form');
	const progressBar = document.getElementById('upload-progress');
	const statusText = document.getElementById('upload-status');
	const submitButton = document.getElementById('upload-submit');

	if (form) {
		form.addEventListener('submit', function (e) {
			e.preventDefault();

			const formData = new FormData(form);

			const xhr = new XMLHttpRequest();
			xhr.open('PUT', form.action, true);

			progressBar.style.display = 'block';
			statusText.textContent = 'Uploading...';
			submitButton.disabled = true;

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

					fetch('/upload', {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json'
						},
						body: JSON.stringify({
							upload_url: data.upload_url,
							upload_hash: data.upload_hash,
							title: formData.get('video-title'),
							description: formData.get('video-desc'),
						})
					}).then(() => {
						setTimeout(() => {
							window.location.href = '/watch/waitfor/' + data.upload_hash;
						}, 1000);
						statusText.textContent = 'Video uploaded successfully! Taking you to your future video...';
					})
				} else {
					statusText.textContent = 'Upload failed. Please try again.';
					resetUploadForm();
				}
			};

			xhr.onerror = function () {
				statusText.textContent = 'An error occurred during upload.';
				resetUploadForm();
			};

			const file = document.getElementById('file-upload').files[0];
			xhr.setRequestHeader('Content-Type', file.type || 'video/mp4');
			xhr.send(file);
		});
	}
});

function resetUploadForm() {
	const form = document.getElementById('upload-form');
	if (form) {
		form.reset();
		document.getElementById('upload-text').textContent = 'Click or drag file here to upload';
		document.getElementById('upload-progress').style.display = 'none';
		document.getElementById('upload-status').textContent = '';
		document.getElementById('upload-submit').disabled = false;
	}
}
