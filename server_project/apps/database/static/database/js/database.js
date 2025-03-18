document.getElementById("folder-rename-modal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            document.getElementById("folder-rename-name").value = data.name;
        },
        onError: (error) => {
            showFeedback('Error fetching folder infos: ' + error.message, 'danger');
        }
    });
});

document.getElementById("image-edit-modal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            document.getElementById("image-edit-name").value = data.name;
            document.getElementById("image-edit-information").value = data.information;
            document.getElementById("image-edit-visibility").value = data.is_public;
        },
        onError: (error) => {
            showFeedback('Error fetching image infos: ' + error.message, 'danger');
            alert('Failed to fetch image infos. Please try again.');
            location.reload();
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
                "Parent": data.parent_path || '-',
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

document.getElementById("image-detail-modal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;
    const listElement = document.getElementById('image-detail-list');

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            listElement.innerHTML = '';
            const details = {
                "Name": data.name || '-',
                "Information": data.information || '-',
                "Author": data.author || '-',
                "Folder": data.folder_name || '-',
                "Metadata": (() => {
                    const dl = document.createElement('dl');
                    dl.className = 'row';
                    createDetailList(dl, data.metadata)
                    return dl.outerHTML;
                })(),
                "Associated Image": `<img src="${data.associated_image || ''}" class="img-fluid" alt="">`,
                "File": data.file_name || '-',
                "Visibility": data.is_public ? 'Public' : 'Private',
                "Created": data.created_at_formatted || '-',
                "Updated": data.updated_at_formatted || '-'
            }
            createDetailList(listElement, details);
        },
        onError: (error) => {
            showFeedback('Error fetching image details: ' + error.message, 'danger');
        }
    });
});

handleModalShow("folder-rename-modal", "folder-rename-form");
handleModalShow("folder-delete-modal", "folder-delete-form");
handleModalShow("image-edit-modal", "image-edit-form");
handleModalShow("image-delete-modal", "image-delete-form");

handleMoveModalShow("folder-move-modal", "folder-move-form", "folder");
handleMoveModalShow("image-move-modal", "image-move-form", "file");

document.getElementById('annotation-rename-modal').addEventListener('show.bs.modal', function (event) {
    let button = event.relatedTarget;

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            document.getElementById("annotation-rename-name").value = data.name;
        },
        onError: (error) => {
            showFeedback('Error fetching annotation infos: ' + error.message, 'danger');
        }
    });
})

document.getElementById('annotation-manage-modal').addEventListener('show.bs.modal', function (event) {
    let button = event.relatedTarget;
    const listElement = document.getElementById('annotation-list');

    fetchData({
        url: button.dataset.url,
        onSuccess: (data) => {
            listElement.innerHTML = '';
            if (data.length === 0) {
                const alert = document.createElement('div');
                alert.classList.add('alert', 'alert-warning', 'mt-3');
                alert.role = 'alert';
                alert.textContent = 'No annotations yet.';
                listElement.appendChild(alert);
                return;
            }
            data.forEach(annotation => {
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item d-flex justify-content-between align-items-center';

                const listItemName = document.createElement('div');
                listItemName.className = 'd-flex align-items-center';

                const listItemIcon = document.createElement('i');
                listItemIcon.className = 'bi bi-file-earmark-text me-2';

                const listItemText = document.createElement('span');
                listItemText.textContent = `${annotation.name} (${annotation.author})`;

                listItemName.append(listItemIcon, listItemText);
                listItem.appendChild(listItemName);

                const listItemActions = document.createElement('div');
                listItemActions.className = 'btn-group btn-group-sm';

                const listItemViewButton = document.createElement('a');
                listItemViewButton.className = 'btn btn-outline-success';
                listItemViewButton.href = annotation.viewer_url;
                listItemViewButton.target = '_blank';
                listItemViewButton.rel = 'noopener noreferrer nofollow';
                listItemViewButton.innerHTML = '<i class="bi bi-eye"></i>';

                listItemActions.appendChild(listItemViewButton);

                if (annotation.editable) {
                    const listItemEditButton = document.createElement('button');
                    listItemEditButton.className = 'btn btn-outline-primary';
                    listItemEditButton.setAttribute('data-bs-toggle', 'modal');
                    listItemEditButton.setAttribute('data-bs-target', '#annotation-rename-modal');
                    listItemEditButton.dataset.url = annotation.url;
                    listItemEditButton.innerHTML = '<i class="bi bi-pencil"></i>';
                    listItemEditButton.addEventListener('click', function () {
                        document.getElementById('annotation-rename-form').dataset.url = annotation.url;
                    });

                    const listItemDeleteButton = document.createElement('button');
                    listItemDeleteButton.className = 'btn btn-outline-danger';
                    listItemDeleteButton.setAttribute('data-bs-toggle', 'modal');
                    listItemDeleteButton.setAttribute('data-bs-target', '#annotation-delete-modal');
                    listItemEditButton.dataset.url = annotation.url;
                    listItemDeleteButton.innerHTML = '<i class="bi bi-trash"></i>';
                    listItemDeleteButton.addEventListener('click', function () {
                        document.getElementById('annotation-delete-form').dataset.url = annotation.url;
                    });

                    listItemActions.append(listItemEditButton, listItemDeleteButton);
                }

                listItem.appendChild(listItemActions);
                listElement.appendChild(listItem);
            });
        },
        onError: (error) => {
            showFeedback('Error fetching annotations: ' + error.message, 'danger');
        }
    });
});

function submitAnnotationModalForm(form, method) {
    const contents = form.querySelector('[data-type="contents"]');
    const loading = form.querySelector('[data-type="loading"]');

    contents?.classList.add('d-none');
    loading?.classList.remove('d-none');

    fetchData({
        url: form.dataset.url,
        method: method,
        data: new FormData(form),
        onSuccess: (data) => {
            $(form).closest('.modal').modal('hide');
        },
        onError: (error) => {
            showFeedback(error.message, 'danger');
            $(form).closest('.modal').modal('hide');
        }
    });
}

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
document.getElementById("image-upload-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "POST");
});
document.getElementById("image-edit-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "PATCH");
});
document.getElementById("image-move-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "PATCH");
});
document.getElementById("image-delete-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "DELETE");
});
document.getElementById("annotation-rename-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitAnnotationModalForm(this, "PATCH");
});
document.getElementById("annotation-delete-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitAnnotationModalForm(this, "DELETE");
});