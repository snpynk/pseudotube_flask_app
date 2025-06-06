function initApp() {
	shaka.polyfill.installAll();

	if (shaka.Player.isBrowserSupported()) {
		initPlayer(document.getElementById('video-player').dataset.url);
	} else {
		console.error('Browser not supported!');
	}
}


async function initPlayer(manifUrl) {
	const like_button = document.getElementById('like-button');
	const delete_button = document.getElementById('delete-button');
	const video = document.getElementById('video-player');
	const like_count = document.getElementById('like-count');
	const commentForm = document.getElementById('comment-form');
	const uiContainer = document.getElementById('video-container');
	const player = new shaka.Player();
	await player.attach(video);
	const ui = new shaka.ui.Overlay(player, uiContainer, video);
	const controls = ui.getControls();

	const video_hash = video.dataset.hash;
	const watch_id = video.dataset.watchid;
	let video_liked = video.dataset.liked === 'True';

	video.addEventListener("loadedmetadata", function () {
		video.parentElement.style.aspectRatio = `${video.videoWidth} / ${video.videoHeight}`;
	});

	ui.configure({
		controlPanelElements: [
			'play_pause',
			'time_and_duration',
			'spacer',
			'volume',
			'quality',
			'resolution_selection',
			'fullscreen'
		]
	});

	try {
		await player.load(manifUrl);
		console.log('The video has now been loaded!');
	} catch (e) {
		console.error(e);
	}


	const stats = player.getStats()

	// Start tracking when the video is playing

	const playbackTimer = setInterval(() => {
		const stats = player.getStats()
		let watched = false;

		if (stats.playTime > (player.seekRange().end * 0.15) && !watched) {
			fetch('/api/video/view/' + watch_id, {
				method: 'POST',
			})
			clearInterval(playbackTimer);
		}
	}, 1000)

	like_button.addEventListener('click', async () => {
		// const likeCount = document.getElementById('like-count');

		console.log(video_liked)
		console.log(video_liked ? 'Unliking video' : 'Liking video');
		try {
			const response = await fetch('/api/video/like/' + video_hash, {
				method: video_liked ? 'DELETE' : 'POST',
			});

			if (response.ok) {
				video_liked = !video_liked;
				like_count.textContent = parseInt(like_count.textContent) + (video_liked ? 1 : -1);
			} else {
				console.error('Failed to like the video');
			}
		} catch (error) {
			console.error('Error liking the video:', error);
		}
	});

	if (delete_button) {
		delete_button.addEventListener('click', async () => {
			if (confirm('Are you sure you want to delete this video? This action cannot be undone.')) {
				try {
					const response = await fetch('/api/video/' + video_hash, {
						method: 'DELETE',
					});

					if (response.ok) {
						window.location.href = '/'; // Redirect to home page after deletion
					} else {
						console.error('Failed to delete the video');
					}
				} catch (error) {
					console.error('Error deleting the video:', error);
				}
			}
		});
	}

	commentForm.addEventListener('submit', async (event) => {
		event.preventDefault();
		const commentInput = document.getElementById("comment-text-input");
		const commentText = commentInput.value.trim();

		if (commentText === '') {
			return; // Don't submit empty comments
		}

		try {
			const response = await fetch('/api/video/comment/' + video_hash, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ text: commentText }),
			});

			if (response.ok) {
				commentInput.value = ''; // Clear the input field
				location.reload(); // Reload to show the new comment
			} else {
				console.error('Failed to post comment');
			}
		} catch (error) {
			console.error('Error posting comment:', error);
		}
	});
}

shaka.polyfill.installAll();
document.addEventListener('DOMContentLoaded', initApp);
