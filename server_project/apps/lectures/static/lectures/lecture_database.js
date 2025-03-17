document.querySelectorAll('.toggle-activity-btn').forEach((button) => button.addEventListener('click', function () {
    fetchData({
        url: this.dataset.url,
        method: 'PATCH',
        onSuccess: (data) => {
            const isActive = data.is_active;
            const icon = this.querySelector('i');
            const updated = this.closest('tr').querySelector('.updated-at');

            icon.classList.toggle("bi-toggle-on", isActive);
            icon.classList.toggle("bi-toggle-off", !isActive);
            icon.nextSibling.textContent = isActive ? " On " : " Off ";

            updated.textContent = data.updated_at_formatted;
        },
        onError: (error) => {
            showFeedback('Error toggling lecture activity: ' + error.message, "danger")
        }
    })
}));

document.getElementById("folder-rename-modal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            document.getElementById("folder-rename-name").value = data.name;
        },
        onError: (error) => {
            showFeedback('Error fetching slide infos: ' + error.message, 'danger');
        }
    });
});

document.getElementById("folder-detail-modal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;
    const listElement = document.getElementById('folder-detail-list');

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            listElement.innerHTML = '';
            const details = {
                "Name": data.name || '-',
                "Contents": `${data.subfolders_count || 0} subfolders, ${data.lectures_count || 0} lectures`,
                "Author": data.author || '-',
                "Parent": data.parent_name || '-',
                "Created": data.created_at_formatted || '-',
                "Updated": data.updated_at_formatted || '-'
            }
            createDetailList(listElement, details);
        },
        onError: (error) => {
            showFeedback('Error fetching folder details: ' + error.message, 'danger');
        }
    });
});

document.getElementById("lecture-detail-modal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;
    const listElement = document.getElementById('lecture-detail-list');

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            listElement.innerHTML = '';
            const details = {
                "Name": data.name || '-',
                "Description": data.description || '-',
                "Author": data.author || '-',
                "Groups": data.group_names || '-',
                "Contents": `${data.slides_count} slides`,
                "Visibility": data.is_active ? 'Active' : 'Inactive',
                "Created": data.created_at_formatted || '-',
                "Updated": data.updated_at_formatted || '-'
            }
            createDetailList(listElement, details);
        },
        onError: (error) => {
            showFeedback('Error fetching lecture details: ' + error.message, "danger");
        }
    })
});

handleModalShow("folder-rename-modal", "folder-rename-form");
handleModalShow("folder-delete-modal", "folder-delete-form");
handleModalShow("lecture-delete-modal", "lecture-delete-form");

handleMoveModalShow("folder-move-modal", "folder-move-form", "folder");
handleMoveModalShow("lecture-move-modal", "lecture-move-form", "file");

document.getElementById("folder-create-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "POST");
});
document.getElementById("folder-rename-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "PATCH");
});
document.getElementById("folder-move-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "PATCH");
});
document.getElementById("folder-delete-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "DELETE");
});
document.getElementById("lecture-create-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "POST");
});
document.getElementById("lecture-move-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "PATCH");
});
document.getElementById("lecture-delete-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "DELETE");
});