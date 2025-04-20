document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll(".slide-upload-progress").forEach((progress) => {
        const slideId = progress.dataset.slideId;

        let protocol = window.location.protocol === "https:" ? "wss" : "ws";
        let socket = new WebSocket(`${protocol}://${window.location.host}/ws/slide/${slideId}/`);

        socket.onopen = function () {
            console.log(`Connected to ${protocol.toUpperCase()}`);
        };
        socket.onmessage = function (event) {
            const data = JSON.parse(event.data);
            if (data.event === "slide_initialize") {
                const progresstext = document.getElementById(`slide-${data.slide_id}-progress-text`);
                progresstext.innerText = "Initializing..";
                if (data.completed) {
                    showFeedback(`Slide '${data.slide_name}' initialized successfully.\nRefresh to see changes.`, 'success')
                }
            } else if (data.event === "progress_update") {
                progress.ariaValueNow = data.progress;
                const progressbar = document.getElementById(`slide-${data.slide_id}-progress-bar`);
                const progresstext = document.getElementById(`slide-${data.slide_id}-progress-text`);
                progressbar.style.width = `${data.progress}%`;
                progresstext.innerText = "Building..";
                if (data.progress === 100) {
                    progressbar.classList.remove("progress-bar-animated");
                    progressbar.classList.remove("progress-bar-striped");
                    progressbar.classList.add("bg-success");
                    progresstext.innerText = "Completed";
                    setTimeout(() => {
                        progress.remove();
                    }, 2000)
                    socket.close();
                    showFeedback(`Slide '${data.slide_name}' finished processing.`, 'success')
                } else if (data.progress === -1) {
                    progress.classList.remove("bg-secondary");
                    progress.classList.add("bg-danger");
                    progresstext.innerText = "Failed";
                    socket.close();
                    showFeedback(`Slide '${data.slide_name}' failed to process.`, 'danger')
                }
            }
        };
        socket.onclose = function () {
            console.log("WebSocket closed");
        };
        socket.onerror = function (error) {
            console.error("WebSocket error:", error);
        };
    });

    document.getElementById("folder-rename-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;

        drfRequest({
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

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                document.getElementById("image-edit-name").value = data.name;
                document.getElementById("image-edit-information").value = data.information;
                document.getElementById("image-edit-access-level").value = data.is_public;
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

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = '';
                const details = {
                    "Name": data.name || '-',
                    "Contents": `${data.child_count || 0} folders, ${data.file_count || 0} slides in this folder`,
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

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = '';

                const fileDl = document.createElement('dl');
                fileDl.className = 'row';
                const downloadLink = document.createElement('a');
                downloadLink.href = data.file_details.file_url;
                downloadLink.className = 'text-decoration-none';
                downloadLink.innerHTML = 'Original <i class="bi bi-download"></i>';
                const repairButton = document.createElement('span');
                repairButton.role = 'button';
                repairButton.className = 'text-warning';
                repairButton.dataset.bsToggle = 'modal';
                repairButton.dataset.bsTarget = '#image-rebuild-modal';
                repairButton.dataset.url = data.file_details.rebuild_url;
                repairButton.innerHTML = 'Repair <i class="bi bi-wrench"></i>';
                if (data.file_details.building) {
                    repairButton.ariaDisabled = true;
                    repairButton.className = 'text-muted';
                    repairButton.tabIndex = -1;
                    repairButton.style.pointerEvents = 'none';
                }
                const fileDetails = {
                    "Name": data.file_details.name || '-',
                    "Size": data.file_details.size || '-',
                    "Download": downloadLink.outerHTML,
                    "Repair": repairButton.outerHTML,
                };
                createDetailList(fileDl, fileDetails);

                const metadataDl = document.createElement('dl');
                metadataDl.className = 'row';
                const metadataDetails = {
                    "Created": data.metadata.created || '-',
                    "SourceLens": data.metadata.sourceLens || '-',
                };
                createDetailList(metadataDl, metadataDetails);

                const details = {
                    "Name": data.name || '-',
                    "Information": data.information || '-',
                    "Author": data.author || '-',
                    "Folder": data.folder_name || '-',
                    "File": fileDl.outerHTML,
                    "Associated Image": `<img src="${data.associated_image || ''}" class="img-fluid" alt="">`,
                    "Metadata": metadataDl.outerHTML,
                    "Access Level": data.is_public ? 'Public' : `Private (${data.owner_group_name})`,
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
    handleModalShow("image-rebuild-modal", "image-rebuild-form");

    handleMoveModalShow("folder-move-modal", "folder-move-form", "folder");
    handleMoveModalShow("image-move-modal", "image-move-form", "file");

    document.getElementById('annotation-rename-modal').addEventListener('show.bs.modal', function (event) {
        let button = event.relatedTarget;

        drfRequest({
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

        drfRequest({
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
                const thumbnail = document.createElement('img');
                thumbnail.src = API_ROUTES.slideDetail(item.id) + 'thumbnail/';
                thumbnail.className = 'me-2';
                thumbnail.style.height = '25px';
                thumbnail.alt = "";
                listItem.append(thumbnail);
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
                url: API_ROUTES.imageFolders + 'tree/',
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
                const thumbnail = document.createElement('img');
                thumbnail.src = API_ROUTES.slideDetail(item.id) + 'thumbnail/';
                thumbnail.className = 'me-2';
                thumbnail.style.height = '25px';
                thumbnail.alt = "";
                title.append(thumbnail);
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
    handleModalFormSubmit("image-edit-form");
    handleModalFormSubmit("image-move-form");
    handleModalFormSubmit("image-delete-form");
    handleModalFormSubmit("image-rebuild-form");

    handleAnnotationModalFormSubmit("annotation-rename-form");
    handleAnnotationModalFormSubmit("annotation-delete-form");

    document.getElementById("image-upload-form").addEventListener("submit", function (event) {
        event.preventDefault();
        const modalElement = document.getElementById("image-upload-modal");
        freezeModal(modalElement);
        const loading = this.querySelector('[data-type="loading"]');
        loading?.classList.remove('d-none');

        submitForm({
            form: this,
            onSuccess: (data) => {
                location.reload();
            },
            onError: (error) => {
                unfreezeModal(modalElement);
                loading?.classList.add('d-none');
            }
        })
    });

    document.getElementById("image-search-form").addEventListener("submit", function (event) {
        event.preventDefault();
        const query = document.getElementById("image-search-input").value;
        if (!query) {
            return;
        }
        const url = this.dataset.url + `?search=${encodeURIComponent(query)}`;
        fetchResults(url);
    });

});

function handleAnnotationModalFormSubmit(formId) {
    document.getElementById(formId).addEventListener("submit", function (event) {
        event.preventDefault();
        submitForm({
            form: this,
            onSuccess: (data) => {
                $(this).closest('.modal').modal('hide');
            }
        })
    })
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
                    url = API_ROUTES.imageFolderDetail(currentItem.id);
                    method = 'PATCH';
                    data = {parent: destinationId};
                } else if (currentItem.type === 'slide') {
                    url = API_ROUTES.slideDetail(currentItem.id);
                    method = 'PATCH';
                    data = {folder: destinationId};
                }
            } else if (actionType === 'delete') {
                if (currentItem.type === 'folder') {
                    url = API_ROUTES.imageFolderDetail(currentItem.id);
                    method = 'DELETE';
                } else if (currentItem.type === 'slide') {
                    url = API_ROUTES.slideDetail(currentItem.id);
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
