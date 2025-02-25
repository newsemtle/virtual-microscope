document.getElementById("detailLectureModal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;

    fetch(button.dataset.url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
        },
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    console.error('Error fetching lecture details:', errorData.details);
                    throw new Error('Failed to fetch lecture details');
                });
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('detail-lecture-name').textContent = data.name || '-';
            document.getElementById('detail-lecture-description').textContent = data.description || '-';
            document.getElementById('detail-lecture-contents').textContent = `${data.slides_count || 0} slides`;
            document.getElementById('detail-lecture-author').textContent = data.author || '-';
            document.getElementById('detail-lecture-groups').textContent = data.group_names || '-';
            document.getElementById('detail-lecture-activity').textContent = data.is_active ? 'On' : 'Off';
            document.getElementById('detail-lecture-created').textContent = data.created_at_formatted || '-';
            document.getElementById('detail-lecture-updated').textContent = data.updated_at_formatted || '-';
        })
        .catch(error => {
            console.error('Error fetching lecture details:', error);
        });
});

document.querySelectorAll('.toggle-activity-btn').forEach((button) => button.addEventListener('click', function () {
    fetch(this.dataset.url, {
        method: 'PATCH',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
        },
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    console.error('Error toggling lecture activity:', errorData.details);
                    throw new Error('Failed to toggle lecture activity');
                });
            }
            return response.json();
        })
        .then(data => {
            const isActive = data.is_active;
            const icon = this.querySelector('i');
            const updated = this.closest('tr').querySelector('.updated-at');

            icon.classList.toggle("bi-toggle-on", isActive);
            icon.classList.toggle("bi-toggle-off", !isActive);
            icon.nextSibling.textContent = isActive ? " On " : " Off ";

            updated.textContent = data.updated_at_formatted;
        })
        .catch(error => {
            console.error('Error toggling lecture activity:', error);
        });
}));