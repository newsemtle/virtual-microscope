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
                    "이름": data.name || '-',
                    "내용": `${data.child_count || 0} 폴더, ${data.lecture_count || 0} 강의`,
                    "작성자": data.author || '-',
                    "관리자": data.manager || '-',
                    "상위폴더": data.parent_path || '-',
                    "생성일": data.created_at_formatted || '-',
                    "수정일": data.updated_at_formatted || '-'
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
                    "이름": data.name || '-',
                    "설명": data.description || '-',
                    "내용": `${data.slide_count} 슬라이드`,
                    "작성자": data.author || '-',
                    "관리자": data.manager || '-',
                    "폴더": data.folder_name || '-',
                    "공개 상태": data.is_active ? '공개' : '비공개',
                    "공개대상그룹": data.group_names.map(group => `<span class="badge text-bg-light border border-dark me-2">${group}</span>`).join('') || '-',
                    "생성일": data.created_at_formatted || '-',
                    "수정일": data.updated_at_formatted || '-'
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
                        input.disabled = user.id.toString() === sendForm.dataset.managerId;

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

    document.getElementById('bulk-move-modal').addEventListener('show.bs.modal', function (event) {
        let button = event.relatedTarget;

        const message = this.querySelector('[data-type="message"]');
        message.classList.add('d-none');

        const continueButton = this.querySelector('.continue');
        continueButton.dataset.type = button.dataset.type;

        const treeContainer = this.querySelector('.tree-container');
        treeContainer.innerHTML = '';
        treeContainer.addEventListener('click', function (event) {
            const radio = event.target.closest('input[type="radio"]');
            if (radio) {
                continueButton.dataset.destination = radio.value;
            }
        })

        let itemType = "file";
        let foldersToMove = [];
        for (const item of getSelectedItems()) {
            if (item.type === 'folder') {
                itemType = "folder";
                foldersToMove.push(item.id);
            }
        }

        drfRequest({
            url: API_ROUTES.lectureFolders + 'tree/',
            onSuccess: (data) => {
                renderMoveTree(treeContainer, data, itemType, foldersToMove);
            },
            onError: (error) => {
                message.textContent = error.message;
                message.classList.remove('d-none');
            }
        });

        const modal = this;
        continueButton.addEventListener('click', function (event) {
            if (this.dataset.destination === undefined) {
                message.textContent = 'Please select a destination folder.';
                message.classList.remove('d-none');
                return;
            }

            const confirmationModal = document.getElementById('confirmation-modal');
            const confirmButton = confirmationModal.querySelector('.continue');
            confirmButton.dataset.type = this.dataset.type;
            confirmButton.dataset.destination = this.dataset.destination;

            bootstrap.Modal.getOrCreateInstance(modal).hide();
            bootstrap.Modal.getOrCreateInstance(confirmationModal).show();
        });
    });

    document.getElementById('confirmation-modal').addEventListener('show.bs.modal', function (event) {
        const continueButton = this.querySelector('.continue');
        continueButton.classList.remove('btn-warning', 'btn-danger');

        const title = this.querySelector('.modal-title');
        const body = this.querySelector('.modal-body');
        body.innerHTML = '';

        const selectedItems = getSelectedItems();

        if (selectedItems.length === 0) {
            title.textContent = '선택 항목';
            continueButton.classList.add('btn-secondary');
            continueButton.textContent = '다음';
            continueButton.disabled = true;
            const info = document.createElement('div');
            info.className = 'alert alert-warning mt-3';
            info.role = 'alert';
            info.textContent = '선택 항목이 없습니다.';
            body.appendChild(info);
            return;
        }

        if (continueButton.dataset.type === 'move') {
            title.textContent = '선택 항목 이동';
            continueButton.classList.add('btn-warning');
            continueButton.textContent = '이동';

            const info = document.createElement('p');
            info.className = 'text-warning';
            info.textContent = `정말로 선택한 ${selectedItems.length}개 항목을 이동하시겠습니까?`
            body.appendChild(info);
        } else if (continueButton.dataset.type === 'delete') {
            title.textContent = '선택 항목 삭제';
            continueButton.classList.add('btn-danger');
            continueButton.textContent = '삭제';

            const info = document.createElement('p');
            info.className = 'text-danger';
            info.textContent = `정말로 선택한 ${selectedItems.length}개 항목을 삭제하시겠습니까?`
            body.appendChild(info);
        } else {
            title.textContent = 'Error';
            continueButton.classList.add('btn-danger');
            continueButton.textContent = 'Error';
            continueButton.disabled = true;
            body.innerHTML = 'Error';
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

        const selectedItems = getSelectedItems();

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
        continueButton.textContent = '닫기';
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

function getSelectedItems() {
    let selectedItems = [];
    document.querySelectorAll('[name="item-checkbox"]').forEach((item) => {
        if (item.checked) {
            selectedItems.push({
                type: item.dataset.type,
                id: item.value,
                name: item.dataset.name,
            });
        }
    });
    return selectedItems;
}

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
                    data = {parent: parseInt(destinationId)};
                } else if (currentItem.type === 'lecture') {
                    url = API_ROUTES.lectureDetail(currentItem.id);
                    method = 'PATCH';
                    data = {folder: parseInt(destinationId)};
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
