//we are not currently using this. currently the js code is in the home.html
// Fetch posts from the backend and display them
function fetchPosts() {
    fetch('/fetch_posts')
        .then(response => response.json())
        .then(posts => {
            const feed = document.getElementById('feed');
            feed.innerHTML = ''; // Clear "Loading" message

            // Loop through posts and display them
            posts.forEach(post => {
                const postElement = document.createElement('div');
                postElement.classList.add('post');

                postElement.innerHTML = `
                    <h3>${post.username}</h3>
                    <img src="${post.image_url}" alt="Post Image">
                    <p>${post.content}</p>
                    <small>Posted on: ${new Date(post.created_at).toLocaleString()}</small>
                    <form class="comment-form" data-post-id="${post.post_id}">
                        <textarea name="content" placeholder="Write a comment..." required></textarea>
                        <button type="submit">Comment</button>
                    </form>
                    <div class="comments" id="comments-${post.post_id}">
                        <p>Loading comments...</p>
                    </div>
                `;
                feed.appendChild(postElement);
            });
        })
        .catch(error => {
            console.error('Error fetching posts:', error);
            const feed = document.getElementById('feed');
            feed.innerHTML = '<p>Failed to load posts.</p>';
        });
}

// Listen for comment form submissions
document.addEventListener('submit', function (event) {
    if (event.target.matches('.comment-form')) {
        event.preventDefault(); // Prevent the default form submission

        const form = event.target;
        const postId = form.getAttribute('data-post-id'); // Get post_id from the form's data attribute
        const content = form.querySelector('textarea[name="content"]').value;

        if (!postId) {
            console.error('Error: post_id is missing.');
            return;
        }

        // Send the comment to the backend
        fetch('/add_comment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                post_id: postId,
                user_id: 1, // Hardcoding user_id for now, replace with dynamic user_id if available
                content: content,
            }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to add comment');
            }
            return response.json();
        })
        .then(data => {
            console.log('Comment added:', data);
            // Reload comments for the post
            loadComments(postId);
            form.reset(); // Clear the comment form
        })
        .catch(error => {
            console.error('Error adding comment:', error);
        });
    }
});

// Fetch posts when the page loads
fetchPosts();
