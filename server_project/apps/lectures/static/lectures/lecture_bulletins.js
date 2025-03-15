document.addEventListener('DOMContentLoaded', function (event) {
    const lectureList = document.getElementById('lecture-list');

    lectureList.addEventListener('click', function (event) {
        const actionElement = event.target.closest('[data-action]');
        if (!actionElement) return;

        const action = actionElement.dataset.action;

        if (action === 'hide') {
            event.preventDefault();
            const listItem = actionElement.closest('tr');
            listItem.remove();
            fetchData({
                url: actionElement.dataset.url,
                method: 'PATCH',
                onError: (error) => {
                    showFeedback('Error hiding the lecture: ' + error.message, 'danger');
                }
            })

            // if there's no more lectures, show the empty message
            if (lectureList.querySelectorAll('tr').length === 0) {
                const lectureTableContainer = document.getElementById('lecture-table-container');
                const emptyMessage = document.getElementById('lecture-empty-message')
                lectureTableContainer.remove();
                emptyMessage.classList.remove('d-none');
            }
        }
    });
});