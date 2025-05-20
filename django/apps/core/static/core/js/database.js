document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("folder-rename-modal").addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
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

    handleModalShow("folder-rename-modal", "folder-rename-form");
    handleModalShow("folder-delete-modal", "folder-delete-form");

    handleMoveModalShow("folder-move-modal", "folder-move-form", "folder");

    handleModalFormSubmit("folder-create-form");
    handleModalFormSubmit("folder-rename-form");
    handleModalFormSubmit("folder-move-form");
    handleModalFormSubmit("folder-delete-form");

    document.getElementById("item-checkbox-all")?.addEventListener("click", function (event) {
        const checkboxes = document.querySelectorAll("[name='item-checkbox']");
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });

    document.querySelectorAll("[name='item-checkbox']")?.forEach((checkbox) => {
        checkbox.addEventListener("click", function (event) {
            const checkboxes = document.querySelectorAll("[name='item-checkbox']");
            document.getElementById("item-checkbox-all").checked = [...checkboxes].every(checkbox => checkbox.checked);
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

    document.getElementById("action-progress-modal").addEventListener("hidden.bs.modal", function (event) {
        window.location.reload();
    });

});

function handleModalFormSubmit(formId) {
    document.getElementById(formId).addEventListener("submit", function (event) {
        event.preventDefault();
        submitForm({
            form: this,
            onSuccess: (data) => {
                location.reload();
            },
        });
    });
}

function handleModalShow(modalId, formId) {
    document.getElementById(modalId).addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        document.getElementById(formId).dataset.url = button.dataset.url;
    });
}

function handleMoveModalShow(modalId, formId, itemType) {
    document.getElementById(modalId).addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        document.getElementById(formId).dataset.url = button.dataset.url;

        drfRequest({
            url: button.dataset.urlTree,
            onSuccess: (data) => {
                const treeContainer = this.querySelector(".folder-tree-container");
                populateMoveTree(treeContainer, data, itemType, [button.dataset.itemId]);
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get folder tree."), "danger");
            },
        });
    });
}

function populateMoveTree(container, data, itemType, movingFolderIds) {
    container.innerHTML = "";
    if (data.length === 0) {
        const alert = document.createElement("div");
        alert.classList.add("alert", "alert-warning", "mt-3");
        alert.role = "alert";
        alert.textContent = gettext("No folders available.");
        container.appendChild(alert);
        return;
    }
    if (itemType === "folder") {
        container.appendChild(createMoveTree(data, itemType, movingFolderIds));
    } else {
        container.appendChild(createMoveTree(data, itemType));
    }
}

function createMoveTree(data, itemType, movingFolderIds = []) {
    const ul = document.createElement("ul");
    ul.className = "list-unstyled mb-0";

    if (!["folder", "file"].includes(itemType)) return ul;

    data.forEach(item => {
        const movingFolder = itemType === "folder" && movingFolderIds.includes(item.id?.toString());
        const showChildren = item.children?.length > 0 && !movingFolder;

        const li = document.createElement("li");

        const input = document.createElement("input");
        input.className = "form-check-input me-2";
        input.type = "radio";
        input.id = `folder-${item.id}`;
        input.name = itemType === "folder" ? "parent" : "folder";
        input.value = item.id;
        input.required = true;
        input.disabled = movingFolder || (itemType === "folder" && !item.id);

        const icon = document.createElement("i");
        icon.className = "bi bi-chevron-right me-2 text-muted";
        icon.type = "button";

        const label = document.createElement("label");
        label.className = "form-check-label";
        label.htmlFor = input.id;
        label.innerHTML = `<i class="bi bi-folder text-warning me-2"></i> ${item.name}`;

        const ulChildContainer = document.createElement("div");
        if (showChildren) {
            icon.classList.remove("text-muted");
            icon.dataset.bsToggle = "collapse";
            icon.setAttribute("href", "#collapse-" + item.id);
            icon.role = "button";

            ulChildContainer.className = "collapse";
            ulChildContainer.id = "collapse-" + item.id;

            ulChildContainer.addEventListener("show.bs.collapse", function (event) {
                event.stopPropagation();
                icon.classList.remove("bi-chevron-right");
                icon.classList.add("bi-chevron-down");
            });
            ulChildContainer.addEventListener("hide.bs.collapse", function (event) {
                event.stopPropagation();
                icon.classList.remove("bi-chevron-down");
                icon.classList.add("bi-chevron-right");
            });

            const ulChild = createMoveTree(item.children, itemType, movingFolderIds);
            ulChild.classList.add("ms-4");
            ulChildContainer.appendChild(ulChild);
        }

        li.append(input, icon, label, ulChildContainer);
        ul.appendChild(li);
    });

    return ul;
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

function processBulkAction(databaseType, items, actionType, destinationId = null) {
    const maxThreads = 5;
    let index = 0;
    let completed = 0;

    return new Promise((resolve) => {
        function next() {
            if (index >= items.length) return;

            const currentItem = items[index++];
            const itemStatus = document.querySelector(`[data-item="${currentItem.type}-${currentItem.id}"]`);

            let url, method, data = {};

            if (databaseType === "image") {
                if (currentItem.type === "folder") {
                    url = API_ROUTES.imageFolders.detail(currentItem.id).base;
                } else if (currentItem.type === "slide") {
                    url = API_ROUTES.slides.detail(currentItem.id).base;
                }
            } else if (databaseType === "lecture") {
                if (currentItem.type === "folder") {
                    url = API_ROUTES.lectureFolders.detail(currentItem.id).base;
                } else if (currentItem.type === "lecture") {
                    url = API_ROUTES.lectures.detail(currentItem.id).base;
                }
            }

            if (actionType === "move") {
                method = "PATCH";
                const destinationType = currentItem.type === "folder" ? "parent" : "folder";
                data[destinationType] = parseInt(destinationId, 10);
            } else if (actionType === "delete") {
                method = "DELETE";
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
                    itemStatus.dataset.bsTooltip = "true";
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
