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
            const progressbar = document.getElementById(`slide-${data.slide_id}-progress-bar`);
            const progressText = document.getElementById(`slide-${data.slide_id}-progress-text`);
            const progress = document.getElementById(`slide-${data.slide_id}-progress`);

            // update tooltip
            progress.dataset.bsOriginalTitle = data.status;

            if (data.event === "slide_initialize") {
                progressText.innerText = "Initializing..";
                if (data.completed) {
                    // reload thumbnail
                    const thumbnail = document.getElementById(`slide-${data.slide_id}-thumbnail`);
                    const clone = thumbnail.cloneNode(true);
                    thumbnail.replaceWith(clone);
                }
            } else if (data.event === "progress_update") {
                progressbar.style.width = `${data.progress}%`;
                progressText.innerText = "Building..";
                if (data.progress === 100) {
                    progressbar.classList.remove("progress-bar-animated");
                    progressbar.classList.remove("progress-bar-striped");
                    progressbar.classList.add("bg-success");
                    progressText.innerText = "Completed";
                    setTimeout(() => {
                        progress.remove();
                    }, 2000);
                    socket.close();
                } else if (data.progress === -1) {
                    progress.classList.remove("bg-secondary");
                    progress.classList.add("bg-danger");
                    progressText.innerText = "Failed";
                    socket.close();
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
                showFeedback(gettext("Failed to get current folder information."), "danger");
            },
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
                showFeedback(gettext("Failed to get current image information."), "danger");
            },
        });
    });

    document.getElementById("folder-detail-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        const listElement = document.getElementById("folder-detail-list");

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = "";
                const details = new Map([
                    [gettext("Name"), data.name || "-"],
                    [gettext("Content"), `${data.children_count || 0} ${gettext("Folders")}, ${data.total_file_count || 0} ${gettext("Images")}`],
                    [gettext("Author"), data.author || "-"],
                    [gettext("Manager Group"), data.manager_group || "-"],
                    [gettext("Parent"), data.parent_path || "-"],
                    [pgettext("date", "Created"), formatDate(data.created_at) || "-"],
                    [pgettext("date", "Updated"), formatDate(data.updated_at) || "-"],
                ]);
                populateDetailList(listElement, details);
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get folder details."), "danger");
            },
        });
    });

    document.getElementById("image-detail-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        const listElement = document.getElementById("image-detail-list");

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = "";

                const downloadLink = document.createElement("a");
                downloadLink.href = data.file_details.file_url;
                downloadLink.className = "text-decoration-none";
                downloadLink.innerHTML = "<i class='bi bi-download'></i>";

                const repairButton = document.createElement("span");
                repairButton.role = "button";
                repairButton.className = "text-warning";
                repairButton.dataset.bsToggle = "modal";
                repairButton.dataset.bsTarget = "#image-rebuild-modal";
                repairButton.dataset.url = data.file_details.rebuild_url;
                repairButton.innerHTML = "<i class='bi bi-wrench'></i>";
                if (data.file_details.building) {
                    repairButton.ariaDisabled = true;
                    repairButton.className = "text-muted";
                    repairButton.tabIndex = -1;
                    repairButton.style.pointerEvents = "none";
                }

                const fileDetails = new Map([
                    [gettext("Name"), data.file_details.name || "-"],
                    [gettext("File Size"), data.file_details.size || "-"],
                    [gettext("Download"), downloadLink],
                    [gettext("Repair"), repairButton],
                ]);

                const metadataDetails = new Map([
                    [gettext("Vendor"), data.metadata.vendor || "-"],
                    [gettext("Created"), data.metadata.created || "-"],
                    [gettext("Objective Power"), data.metadata.objective_power || "-"],
                ]);

                const associatedImages = document.createElement("div");
                data.associated_image_names.forEach(name => {
                    const image = document.createElement("img");
                    image.src = API_ROUTES.slides.detail(data.id).associated_image(name);
                    image.className = "img-fluid mb-2";
                    image.style.maxHeight = "150px";
                    image.alt = "";
                    associatedImages.append(image);
                });

                const details = new Map([
                    [gettext("Name"), data.name || "-"],
                    [gettext("Information"), data.information || "-"],
                    [gettext("Author"), data.author || "-"],
                    [gettext("Manager Group"), data.manager_group || "-"],
                    [gettext("Folder"), data.folder_name || "-"],
                    [gettext("Original File"), fileDetails],
                    [gettext("Associated Images"), associatedImages],
                    [gettext("Metadata"), metadataDetails],
                    [gettext("Access Level"), data.is_public ? gettext("Public") : `${gettext("Private")} (${data.manager_group})`],
                    [pgettext("date", "Created"), formatDate(data.created_at) || "-"],
                    [pgettext("date", "Updated"), formatDate(data.updated_at) || "-"],
                ]);
                populateDetailList(listElement, details);
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get image details."), "danger");
            },
        });
    });

    handleModalShow("folder-rename-modal", "folder-rename-form");
    handleModalShow("folder-delete-modal", "folder-delete-form");
    handleModalShow("image-edit-modal", "image-edit-form");
    handleModalShow("image-delete-modal", "image-delete-form");
    handleModalShow("image-rebuild-modal", "image-rebuild-form");

    handleMoveModalShow("folder-move-modal", "folder-move-form", "folder");
    handleMoveModalShow("image-move-modal", "image-move-form", "file");

    document.getElementById("annotation-rename-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                document.getElementById("annotation-rename-name").value = data.name;
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get annotation information."), "danger");
            },
        });
    });

    document.getElementById("annotation-manage-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        const listElement = document.getElementById("annotation-list");

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = "";
                if (data.length === 0) {
                    const alert = document.createElement("div");
                    alert.classList.add("alert", "alert-warning", "mt-3");
                    alert.role = "alert";
                    alert.textContent = gettext("No annotations available.");
                    listElement.appendChild(alert);
                    return;
                }
                data.forEach(annotation => {
                    const li = document.createElement("li");
                    li.className = "list-group-item d-flex justify-content-between align-items-center";

                    const name = document.createElement("div");
                    name.className = "d-flex align-items-center";

                    const icon = document.createElement("i");
                    icon.className = "bi bi-file-earmark-text me-2";

                    const text = document.createElement("span");
                    text.textContent = `${annotation.name} (${annotation.author})`;

                    name.append(icon, text);
                    li.appendChild(name);

                    const actions = document.createElement("div");
                    actions.className = "btn-group btn-group-sm";

                    const viewButton = document.createElement("a");
                    viewButton.className = "btn btn-outline-success";
                    viewButton.href = annotation.viewer_url;
                    viewButton.target = "_blank";
                    viewButton.rel = "noopener noreferrer nofollow";
                    viewButton.innerHTML = "<i class='bi bi-eye'></i>";

                    actions.appendChild(viewButton);

                    if (annotation.editable) {
                        const editButton = document.createElement("button");
                        editButton.className = "btn btn-outline-primary";
                        editButton.dataset.bsToogle = "modal";
                        editButton.dataset.bsTarget = "#annotation-rename-modal";
                        editButton.dataset.url = annotation.url;
                        editButton.innerHTML = "<i class='bi bi-pencil'></i>";
                        editButton.addEventListener("click", function () {
                            document.getElementById("annotation-rename-form").dataset.url = annotation.url;
                        });

                        const deleteButton = document.createElement("button");
                        deleteButton.className = "btn btn-outline-danger";
                        deleteButton.dataset.bsToggle = "modal";
                        deleteButton.dataset.bsTarget = "#annotation-delete-modal";
                        deleteButton.innerHTML = "<i class='bi bi-trash'></i>";
                        deleteButton.addEventListener("click", function () {
                            document.getElementById("annotation-delete-form").dataset.url = annotation.url;
                        });

                        actions.append(editButton, deleteButton);
                    }

                    li.appendChild(actions);
                    listElement.appendChild(li);
                });
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get annotations."), "danger");
            },
        });
    });

    document.getElementById("bulk-move-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;

        const message = this.querySelector("[data-type='message']");
        message.classList.add("d-none");

        const continueButton = this.querySelector(".continue");
        continueButton.dataset.type = button.dataset.type;

        const treeContainer = this.querySelector(".tree-container");
        treeContainer.innerHTML = "";

        let itemType = "file";
        let foldersToMove = [];
        for (const item of getSelectedItems()) {
            if (item.type === "folder") {
                itemType = "folder";
                foldersToMove.push(item.id);
            }
        }

        drfRequest({
            url: API_ROUTES.imageFolders.list.tree,
            onSuccess: (data) => {
                populateMoveTree(treeContainer, data, itemType, foldersToMove);
            },
            onError: (error) => {
                message.textContent = error.message;
                message.classList.remove("d-none");
            },
        });
    });

    document.getElementById("bulk-move-modal").querySelector(".continue").addEventListener("click", function (event) {
        const modal = this.closest(".modal");
        const treeContainer = modal.querySelector(".tree-container");
        const message = modal.querySelector("[data-type='message']");
        let destination;
        treeContainer.querySelectorAll("input[type='radio']").forEach(radio => {
            if (radio.checked) {
                destination = radio.value;
            }
        });
        if (destination === undefined) {
            message.textContent = gettext("Please select a destination folder.");
            message.classList.remove("d-none");
            return;
        }

        const confirmationModal = document.getElementById("confirmation-modal");
        const confirmButton = confirmationModal.querySelector(".continue");
        confirmButton.dataset.type = this.dataset.type;
        confirmButton.dataset.destination = destination;

        bootstrap.Modal.getOrCreateInstance(modal).hide();
        bootstrap.Modal.getOrCreateInstance(confirmationModal).show();
    });

    document.getElementById("confirmation-modal").addEventListener("show.bs.modal", function (event) {

        const continueButton = this.querySelector(".continue");
        continueButton.classList.remove("btn-warning", "btn-danger");

        const button = event.relatedTarget;
        if (button) {
            continueButton.dataset.type = button.dataset.type;
        }

        const title = this.querySelector(".modal-title");
        const body = this.querySelector(".modal-body");
        body.innerHTML = "";

        const selectedItems = getSelectedItems();

        if (selectedItems.length === 0) {
            title.textContent = gettext("Selected Items");
            continueButton.classList.add("btn-secondary");
            continueButton.textContent = gettext("Next");
            continueButton.disabled = true;
            const info = document.createElement("div");
            info.className = "alert alert-warning mt-3";
            info.role = "alert";
            info.textContent = gettext("No items selected.");
            body.appendChild(info);
            return;
        }

        if (continueButton.dataset.type === "move") {
            title.textContent = gettext("Move Selected Items");
            continueButton.classList.add("btn-warning");
            continueButton.textContent = gettext("Move");

            const info = document.createElement("p");
            info.className = "text-warning";
            info.textContent = interpolate(ngettext(
                "Are you sure you want to move %(count)s item?",
                "Are you sure you want to move %(count)s items?",
                selectedItems.length,
            ), {count: selectedItems.length}, true);
            body.appendChild(info);

        } else if (continueButton.dataset.type === "delete") {
            title.textContent = gettext("Delete Selected Items");
            continueButton.classList.add("btn-danger");
            continueButton.textContent = gettext("Delete");

            const info = document.createElement("p");
            info.className = "text-danger";
            info.textContent = interpolate(ngettext(
                "Are you sure you want to delete %(count)s item?",
                "Are you sure you want to delete %(count)s items?",
                selectedItems.length,
            ), {count: selectedItems.length}, true);
            body.appendChild(info);

        } else {
            title.textContent = "Error";
            continueButton.classList.add("btn-danger");
            continueButton.textContent = "Error";
            continueButton.disabled = true;
            body.innerHTML = "Error";
        }
    });

    document.getElementById("action-progress-modal").addEventListener("show.bs.modal", async function (event) {
        const button = event.relatedTarget;

        freezeModal(this);

        const continueButton = this.querySelector(".continue");
        continueButton.classList.add("btn-secondary");
        continueButton.textContent = `${gettext("Working")}...`;

        const title = this.querySelector(".modal-title");
        const itemListElement = document.getElementById("item-progress-list");
        itemListElement.innerHTML = "";

        const selectedItems = getSelectedItems();

        selectedItems.forEach(item => {
            const listItem = document.createElement("li");
            listItem.className = "list-group-item d-flex align-items-center justify-content-between";

            const title = document.createElement("div");
            title.className = "d-flex align-items-center";

            if (item.type === "folder") {
                const icon = document.createElement("i");
                icon.className = "bi bi-folder text-warning ps-1 me-2";
                icon.style.width = "25px";
                title.append(icon);
            } else {
                const thumbnail = document.createElement("img");
                thumbnail.src = API_ROUTES.slides.detail(item.id).thumbnail;
                thumbnail.className = "me-2";
                thumbnail.style.height = "25px";
                thumbnail.alt = "";
                title.append(thumbnail);
            }

            const listItemName = document.createElement("span");
            listItemName.textContent = item.name;
            title.append(listItemName);

            const status = document.createElement("i");
            status.className = "bi bi-circle text-muted";
            status.dataset.item = `${item.type}-${item.id}`;

            listItem.append(title, status);
            itemListElement.appendChild(listItem);
        });

        if (button.dataset.type === "move") {
            title.textContent = gettext("Move Selected Items");
            await processBulkAction(selectedItems, "move", button.dataset.destination);
        } else if (button.dataset.type === "delete") {
            title.textContent = gettext("Delete Selected Items");
            await processBulkAction(selectedItems, "delete");
        }
        continueButton.classList.remove("btn-secondary");
        continueButton.classList.add("btn-success");
        continueButton.textContent = gettext("Close");
        unfreezeModal(this);
    });

    document.getElementById("action-progress-modal").addEventListener("hidden.bs.modal", function (event) {
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
        const loading = this.querySelector("[data-type='loading']");
        loading?.classList.remove("d-none");

        submitForm({
            form: this,
            onSuccess: (data) => {
                location.reload();
            },
            onError: (error) => {
                unfreezeModal(modalElement);
                loading?.classList.add("d-none");
            },
        });
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
                bootstrap.Modal.getOrCreateInstance(this.closest(".modal")).hide();
            },
        });
    });
}

function getSelectedItems() {
    let selectedItems = [];
    document.querySelectorAll("[name='item-checkbox']").forEach((item) => {
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
            if (actionType === "move") {
                if (currentItem.type === "folder") {
                    url = API_ROUTES.imageFolders.detail(currentItem.id).base;
                    method = "PATCH";
                    data = {parent: parseInt(destinationId)};
                } else if (currentItem.type === "slide") {
                    url = API_ROUTES.slides.detail(currentItem.id).base;
                    method = "PATCH";
                    data = {folder: parseInt(destinationId)};
                }
            } else if (actionType === "delete") {
                if (currentItem.type === "folder") {
                    url = API_ROUTES.imageFolders.detail(currentItem.id).base;
                    method = "DELETE";
                } else if (currentItem.type === "slide") {
                    url = API_ROUTES.slides.detail(currentItem.id).base;
                    method = "DELETE";
                }
            }

            drfRequest({
                url: url,
                method: method,
                data: data,
                onSuccess: () => {
                    itemStatus.classList.remove("text-muted", "bi-circle");
                    itemStatus.classList.add("text-success", "bi-check-circle");
                    checkDone();
                },
                onError: (error) => {
                    itemStatus.classList.remove("text-muted", "bi-circle");
                    itemStatus.classList.add("text-danger", "bi-x-circle");
                    itemStatus.title = error.message;
                    itemStatus.dataset.bsTooltip = "tooltip";
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
