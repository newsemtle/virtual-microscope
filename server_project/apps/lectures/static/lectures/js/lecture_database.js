document.querySelectorAll('.toggle-activity-btn').forEach((button) => button.addEventListener('click', function () {
    fetchData({
        url: this.dataset.url,
        method: 'PATCH',
        onSuccess: (data) => {
            const isActive = data.is_active;
            const icon = this.querySelector('i');

            icon.classList.toggle("bi-toggle-on", isActive);
            icon.classList.toggle("bi-toggle-off", !isActive);
            icon.nextSibling.textContent = isActive ? " On " : " Off ";
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
                "Contents": `${data.subfolders_count || 0} subfolders, ${data.lectures_count || 0} lectures in this folder`,
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
                "Folder": data.folder_name || '-',
                "Groups": data.group_names.map(group => `<span class="badge text-bg-light border border-dark">${group}</span>`).join(' ') || '-',
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

document.getElementById("lecture-copy-modal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;
    document.getElementById("lecture-copy-form").dataset.url = button.dataset.url;

    fetchData({
        url: button.dataset.urlUsers,
        onSuccess: (data) => {
            const usersContainer = this.querySelector('.users-container');
            usersContainer.innerHTML = '';
            if (data.length === 0) {
                const alert = document.createElement('div');
                alert.classList.add('alert', 'alert-warning', 'mt-3');
                alert.role = 'alert';
                alert.textContent = 'No users available.';
                usersContainer.appendChild(alert);
                return;
            }

            const groupUl = document.createElement('ul');
            groupUl.className = 'list-unstyled mb-0';

            data.forEach(group => {
                const groupLi = document.createElement('li');

                const collapseIcon = document.createElement('i');
                collapseIcon.className = 'bi bi-chevron-right me-2 text-muted';
                collapseIcon.dataset.bsToggle = 'collapse';
                collapseIcon.setAttribute('href', '#collapse-' + group.id);
                collapseIcon.role = 'button';

                const groupIcon = document.createElement('i');
                groupIcon.className = 'bi bi-folder text-warning me-2';

                const title = document.createElement('span');
                title.textContent = group.name;

                const userUlContainer = document.createElement('div');
                userUlContainer.className = 'collapse';
                userUlContainer.id = 'collapse-' + group.id;
                userUlContainer.addEventListener('show.bs.collapse', function (event) {
                    event.stopPropagation();
                    collapseIcon.classList.remove('bi-chevron-right');
                    collapseIcon.classList.add('bi-chevron-down');
                });
                userUlContainer.addEventListener('hide.bs.collapse', function (event) {
                    event.stopPropagation();
                    collapseIcon.classList.remove('bi-chevron-down');
                    collapseIcon.classList.add('bi-chevron-right');
                });

                const userUl = document.createElement('ul');
                userUl.className = 'list-unstyled ms-4';
                group.users.forEach(user => {
                    const userLi = document.createElement('li');

                    const input = document.createElement('input');
                    input.className = 'form-check-input me-2';
                    input.type = 'radio';
                    input.id = `user-${user.id}`;
                    input.name = "target";
                    input.value = user.id;
                    input.required = true;

                    const label = document.createElement('label');
                    label.className = 'form-check-label';
                    label.htmlFor = input.id;
                    label.textContent = `${user.full_name} (${user.username})`;

                    userLi.append(input, label);
                    userUl.appendChild(userLi);
                });
                userUlContainer.appendChild(userUl);
                groupLi.append(collapseIcon, groupIcon, title, userUlContainer);
                groupUl.appendChild(groupLi);
            });
            usersContainer.appendChild(groupUl);
        },
        onError: (error) => {
            showFeedback('Error fetching users: ' + error.message, 'danger');
        }
    });
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
    fetchData({
        url: this.dataset.url,
        method: "POST",
        data: new FormData(this),
        onSuccess: (data) => {
            window.open(data.edit_url, "_blank", "noopener,noreferrer");
            location.reload();
        },
        onError: (error) => {
            showFeedback(error.message, 'danger');
            $(this).closest('.modal').modal('hide');
        }
    });
});
document.getElementById("lecture-move-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "PATCH");
});
document.getElementById("lecture-copy-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "POST");
});
document.getElementById("lecture-delete-form").addEventListener("submit", function (event) {
    event.preventDefault();
    submitModalForm(this, "DELETE");
});