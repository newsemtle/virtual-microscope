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

    document.getElementById("image-edit-modal").addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
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
        const button = event.relatedTarget;
        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                const listElement = document.getElementById("folder-detail-list");
                listElement.innerHTML = "";
                const details = new Map([
                    [gettext("Name"), data.name || "-"],
                    [gettext("Content"), `${data.children_count || 0} ${gettext("Folders")}, ${data.total_file_count || 0} ${gettext("Images")}`],
                    [gettext("Author"), data.author || "-"],
                    [gettext("Manager Group"), data.manager_group || "-"],
                    [pgettext("folder", "Parent"), data.parent_path || "-"],
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
        const button = event.relatedTarget;
        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                const listElement = document.getElementById("image-detail-list");
                listElement.innerHTML = "";

                const downloadLink = document.createElement("a");
                downloadLink.href = API_ROUTES.slides.detail(data.id).file;
                downloadLink.className = "text-decoration-none";
                downloadLink.innerHTML = "<i class='bi bi-download'></i>";

                const repairButton = document.createElement("span");
                repairButton.role = "button";
                repairButton.className = "text-warning";
                repairButton.dataset.bsToggle = "modal";
                repairButton.dataset.bsTarget = "#image-rebuild-modal";
                repairButton.dataset.url = API_ROUTES.slides.detail(data.id).rebuild;
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
                    [pgettext("date", "Created"), data.metadata.created || "-"],
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

    document.getElementById("annotation-rename-modal").addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
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
        const button = event.relatedTarget;
        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                const listElement = document.getElementById("annotation-list");
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

                    const text = document.createElement("a");
                    text.className = "text-body text-decoration-none";
                    text.textContent = `${annotation.name} (${annotation.author})`;
                    text.href = `/viewer/${annotation.slide}/?annotation=${annotation.id}`;
                    text.target = "_blank";
                    text.rel = "noopener noreferrer nofollow";

                    name.append(icon, text);
                    li.appendChild(name);

                    const actions = document.createElement("div");
                    actions.className = "btn-group btn-group-sm";

                    if (annotation.editable) {
                        const editButton = document.createElement("button");
                        editButton.className = "btn btn-outline-primary";
                        editButton.title = gettext("Rename");
                        editButton.dataset.bsTooltip = "true";
                        editButton.dataset.bsToggle = "modal";
                        editButton.dataset.bsTarget = "#annotation-rename-modal";
                        editButton.dataset.url = API_ROUTES.annotations.detail(annotation.id).base;
                        editButton.innerHTML = "<i class='bi bi-pencil'></i>";

                        const deleteButton = document.createElement("button");
                        deleteButton.className = "btn btn-outline-danger";
                        deleteButton.title = gettext("Delete");
                        deleteButton.dataset.bsTooltip = "true";
                        deleteButton.dataset.bsToggle = "modal";
                        deleteButton.dataset.bsTarget = "#annotation-delete-modal";
                        deleteButton.dataset.url = API_ROUTES.annotations.detail(annotation.id).base;
                        deleteButton.innerHTML = "<i class='bi bi-trash'></i>";

                        actions.append(editButton, deleteButton);
                    }

                    li.appendChild(actions);
                    listElement.appendChild(li);
                });
                activateTooltips(...listElement.querySelectorAll("[data-bs-tooltip='true']"));
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get annotations."), "danger");
            },
        });
    });

    handleModalShow("image-edit-modal", "image-edit-form");
    handleModalShow("image-delete-modal", "image-delete-form");
    handleModalShow("image-rebuild-modal", "image-rebuild-form");
    handleModalShow("annotation-rename-modal", "annotation-rename-form");
    handleModalShow("annotation-delete-modal", "annotation-delete-form");

    handleMoveModalShow("image-move-modal", "image-move-form", "file");

    document.getElementById("bulk-move-modal").addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;

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

    document.getElementById("action-progress-modal").addEventListener("show.bs.modal", async function (event) {
        const button = event.relatedTarget;
        const actionType = button.dataset.type;
        const destination = button.dataset.destination;

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
            itemListElement.appendChild(listItem);

            const title = document.createElement("div");
            title.className = "d-flex align-items-center";

            const status = document.createElement("i");
            status.className = "bi bi-circle text-muted";
            status.dataset.item = `${item.type}-${item.id}`;

            listItem.append(title, status);

            let image;
            if (item.type === "folder") {
                image = document.createElement("i");
                image.className = "bi bi-folder text-warning ps-1 me-2";
                image.style.width = "25px";
            } else {
                image = document.createElement("img");
                image.src = API_ROUTES.slides.detail(item.id).thumbnail;
                image.className = "me-2";
                image.style.height = "25px";
                image.alt = "";
            }

            const name = document.createElement("span");
            name.textContent = item.name;

            title.append(image, name);
        });

        if (actionType === "move") {
            title.textContent = gettext("Move Selected Items");
            await processBulkAction("image", selectedItems, "move", destination);
        } else if (actionType === "delete") {
            title.textContent = gettext("Delete Selected Items");
            await processBulkAction("image", selectedItems, "delete");
        }
        continueButton.classList.remove("btn-secondary");
        continueButton.classList.add("btn-success");
        continueButton.textContent = gettext("Close");
        unfreezeModal(this);
    });

    handleModalFormSubmit("image-edit-form");
    handleModalFormSubmit("image-move-form");
    handleModalFormSubmit("image-delete-form");
    handleModalFormSubmit("image-rebuild-form");

    document.getElementById("annotation-rename-form").addEventListener("submit", function (event) {
        event.preventDefault();
        submitForm({
            form: this,
            onSuccess: (data) => {
                bootstrap.Modal.getOrCreateInstance(this.closest(".modal")).hide();
                showFeedback(gettext("Renamed annotation successfully!"), "success");
            },
            onError: (error) => {
                showFeedback(gettext("Failed to rename the annotation."), "danger");
            },
        });
    });

    document.getElementById("annotation-delete-form").addEventListener("submit", function (event) {
        event.preventDefault();
        submitForm({
            form: this,
            onSuccess: (data) => {
                bootstrap.Modal.getOrCreateInstance(this.closest(".modal")).hide();
                showFeedback(gettext("Deleted annotation successfully!"), "success");
            },
            onError: (error) => {
                showFeedback(gettext("Failed to delete the annotation."), "danger");
            },
        });
    });

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
        const url = API_ROUTES.images.list.search(encodeURIComponent(query));
        fetchImageSearchResults(url);
    });

});
