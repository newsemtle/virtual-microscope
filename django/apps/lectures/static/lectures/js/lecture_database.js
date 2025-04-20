document.addEventListener('DOMContentLoaded', function (event) {

    document.querySelectorAll('.toggle-activity-btn').forEach((button) => button.addEventListener('click', function () {
        drfRequest({
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

        drfRequest({
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

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = '';
                const details = {
                    "Name": data.name || '-',
                    "Contents": `${data.child_count || 0} folders, ${data.lecture_count || 0} lectures in this folder`,
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

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = '';
                const details = {
                    "Name": data.name || '-',
                    "Description": data.description || '-',
                    "Author": data.author || '-',
                    "Folder": data.folder_name || '-',
                    "Groups": data.group_names.map(group => `<span class="badge text-bg-light border border-dark">${group}</span>`).join(' ') || '-',
                    "Contents": `${data.file_count} slides`,
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
        const duplicateForm = document.getElementById("lecture-duplicate-form");
        const sendForm = document.getElementById("lecture-send-form");
        duplicateForm.dataset.url = button.dataset.duplicateUrl;
        sendForm.dataset.url = button.dataset.sendUrl;

        drfRequest({
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
                        input.disabled = user.id.toString() === sendForm.dataset.ownerId;

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

    let selectedItems = [];

    document.getElementById('item-list-modal').addEventListener('show.bs.modal', function (event) {
        let button = event.relatedTarget;

        const continueButton = this.querySelector('.continue');
        continueButton.dataset.type = button.dataset.type;

        selectedItems = [];
        document.querySelectorAll('[name="item-checkbox"]').forEach((item) => {
            if (item.checked) {
                selectedItems.push({
                    type: item.dataset.type,
                    id: item.value,
                    name: item.dataset.name,
                });
            }
        })

        const itemListElement = document.getElementById('item-selected-list');
        itemListElement.innerHTML = '';
        if (selectedItems.length === 0) {
            itemListElement.innerHTML = '<div class="alert alert-warning">선택된 항목이 없습니다.</div>';
            continueButton.disabled = true;
            return;
        }
        selectedItems.forEach(item => {
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item d-flex align-items-center';

            if (item.type === 'folder') {
                const icon = document.createElement('i');
                icon.className = 'bi bi-folder text-warning ps-1 me-2';
                icon.style.width = '25px';
                listItem.append(icon);
            } else {
                const icon = document.createElement('i');
                icon.className = 'bi bi-journal-text text-primary ps-1 me-2';
                icon.style.width = '25px';
                listItem.append(icon);
            }

            const listItemName = document.createElement('span');
            listItemName.textContent = item.name;
            listItem.append(listItemName);

            itemListElement.appendChild(listItem);
        });
    });

    document.getElementById('bulk-action-modal').addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;

        const continueButton = this.querySelector('.continue');
        continueButton.dataset.type = button.dataset.type;
        continueButton.classList.remove('btn-warning', 'btn-danger');

        const title = this.querySelector('.modal-title');
        const infoContainer = this.querySelector('.info-container');
        infoContainer.innerHTML = '';

        if (button.dataset.type === 'move') {
            title.textContent = '선택 항목 이동';
            continueButton.classList.add('btn-warning');
            continueButton.textContent = '이동';
            infoContainer.classList.add('border', 'rounded', 'p-3');
            infoContainer.addEventListener('click', function (event) {
                const radio = event.target.closest('[name="folder"], [name="parent"]');
                if (radio) {
                    continueButton.dataset.destination = radio.value;
                }
            })

            let itemType = "file";
            let foldersToMove = [];
            for (const item of selectedItems) {
                if (item.type === 'folder') {
                    itemType = "folder";
                    foldersToMove.push(item.id);
                }
            }

            drfRequest({
                url: API_ROUTES.lectureFolders + 'tree/',
                onSuccess: (data) => {
                    renderMoveTree(infoContainer, data, itemType, foldersToMove);
                },
                onError: (error) => {
                    showFeedback('Error fetching folders: ' + error.message, 'danger');
                }
            });
        } else if (button.dataset.type === 'delete') {
            title.textContent = '선택 항목 삭제';
            continueButton.classList.add('btn-danger');
            continueButton.textContent = '삭제';
            infoContainer.classList.remove('border', 'rounded', 'p-3');

            const info = document.createElement('p');
            info.className = 'text-danger';
            info.textContent = `정말로 선택한 ${selectedItems.length}개 항목을 삭제하시겠습니까?`
            infoContainer.appendChild(info);
        } else {
            title.textContent = 'Error';
            continueButton.classList.add('btn-danger');
            continueButton.textContent = 'Error';
            continueButton.disabled = true;
            infoContainer.innerHTML = 'Error';
        }
    });

    document.getElementById('action-progress-modal').addEventListener('show.bs.modal', async function (event) {
        const button = event.relatedTarget;

        freezeModal(this);

        const continueButton = this.querySelector('.continue');
        continueButton.classList.add('btn-secondary');
        continueButton.textContent = "진행중.."

        const title = this.querySelector('.modal-title');
        const itemListElement = document.getElementById('item-progress-list');
        itemListElement.innerHTML = '';
        selectedItems.forEach(item => {
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item d-flex align-items-center justify-content-between';

            const title = document.createElement('div');
            title.className = 'd-flex align-items-center';

            if (item.type === 'folder') {
                const icon = document.createElement('i');
                icon.className = 'bi bi-folder text-warning ps-1 me-2';
                icon.style.width = '25px';
                title.append(icon);
            } else {
                const icon = document.createElement('i');
                icon.className = 'bi bi-journal-text text-primary ps-1 me-2';
                icon.style.width = '25px';
                listItem.append(icon);
            }

            const listItemName = document.createElement('span');
            listItemName.textContent = item.name;
            title.append(listItemName);

            const status = document.createElement('i');
            status.className = 'bi bi-circle text-muted';
            status.dataset.item = `${item.type}-${item.id}`;

            listItem.append(title, status);
            itemListElement.appendChild(listItem);
        });

        if (button.dataset.type === 'move') {
            title.textContent = '선택 항목 이동';
            await processBulkAction(selectedItems, 'move', button.dataset.destination);
        } else if (button.dataset.type === 'delete') {
            title.textContent = '선택 항목 삭제';
            await processBulkAction(selectedItems, 'delete');
        }
        continueButton.classList.remove('btn-secondary');
        continueButton.classList.add('btn-success');
        continueButton.textContent = '완료';
        unfreezeModal(this);
    });

    document.getElementById('action-progress-modal').addEventListener('hidden.bs.modal', function (event) {
        window.location.reload();
    });

    handleModalFormSubmit("folder-create-form");
    handleModalFormSubmit("folder-rename-form");
    handleModalFormSubmit("folder-move-form");
    handleModalFormSubmit("folder-delete-form");
    handleModalFormSubmit("lecture-move-form");
    handleModalFormSubmit("lecture-duplicate-form");
    handleModalFormSubmit("lecture-send-form");
    handleModalFormSubmit("lecture-delete-form");

    document.getElementById("lecture-create-form").addEventListener("submit", function (event) {
        event.preventDefault();
        submitForm({
            form: this,
            onSuccess: (data) => {
                window.location.href = data.edit_url;
            }
        });
    });

});

function processBulkAction(items, actionType, destinationId = null) {
    const maxThreads = 5;
    let index = 0;
    let completed = 0;

    return new Promise((resolve) => {
        function next() {
            if (index >= items.length) return;

            const currentItem = items[index++];
            const itemStatus = document.querySelector(`[data-item="${currentItem.type}-${currentItem.id}"]`);

            let url, method, data;
            if (actionType === 'move') {
                if (currentItem.type === 'folder') {
                    url = API_ROUTES.lectureFolderDetail(currentItem.id);
                    method = 'PATCH';
                    data = {parent: destinationId};
                } else if (currentItem.type === 'lecture') {
                    url = API_ROUTES.lectureDetail(currentItem.id);
                    method = 'PATCH';
                    data = {folder: destinationId};
                }
            } else if (actionType === 'delete') {
                if (currentItem.type === 'folder') {
                    url = API_ROUTES.lectureFolderDetail(currentItem.id);
                    method = 'DELETE';
                } else if (currentItem.type === 'slide') {
                    url = API_ROUTES.lectureDetail(currentItem.id);
                    method = 'DELETE';
                }
            }

            drfRequest({
                url: url,
                method: method,
                data: data,
                onSuccess: () => {
                    itemStatus.classList.remove('text-muted', 'bi-circle');
                    itemStatus.classList.add('text-success', 'bi-check-circle');
                    checkDone();
                },
                onError: (error) => {
                    itemStatus.classList.remove('text-muted', 'bi-circle');
                    itemStatus.classList.add('text-danger', 'bi-x-circle');
                    itemStatus.setAttribute('data-bs-tooltip', 'tooltip');
                    itemStatus.setAttribute('title', error.message);
                    activateTooltips(itemStatus);
                    checkDone();
                },
            });
        }

        function checkDone() {
            completed++;
            if (index < items.length) {
                next();
            }
            if (completed === items.length) {
                resolve();
            }
        }

        for (let i = 0; i < maxThreads && i < items.length; i++) {
            next();
        }
    });
}
