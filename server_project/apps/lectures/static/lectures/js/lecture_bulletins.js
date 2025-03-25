document.addEventListener('DOMContentLoaded', function (event) {
    const lectureItems = document.querySelectorAll('.lecture-item');

    lectureItems.forEach(item => {
        item.addEventListener('click', function (event) {
            const actionElement = event.target.closest('[data-action]');
            if (!actionElement) return;

            const action = actionElement.dataset.action;

            if (action === 'hide') {
                event.preventDefault();
                item.remove();
                fetchData({
                    url: actionElement.dataset.url,
                    method: 'PATCH',
                    onError: (error) => {
                        showFeedback('Error hiding the lecture: ' + error.message, 'danger');
                    }
                })
            }
        });
    })
});