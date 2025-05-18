document.addEventListener("DOMContentLoaded", function (event) {

    document.querySelectorAll(".toggle-status-btn").forEach((button) => button.addEventListener("click", function () {
        drfRequest({
            url: API_ROUTES.lectures.detail(this.dataset.lectureId).toggle_status,
            method: "PATCH",
            onSuccess: (data) => {
                const isOpen = data.is_open;
                const icon = this.querySelector("i");
                const text = this.querySelector("span");

                icon.classList.toggle("bi-toggle-on", isOpen);
                icon.classList.toggle("bi-toggle-off", !isOpen);
                text.textContent = isOpen ? gettext("Open") : gettext("Closed");
            },
            onError: (error) => {
                showFeedback(gettext("Failed to toggle lecture status."), "danger");
            },
        });
    }));

    document.getElementById("folder-rename-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                document.getElementById("folder-rename-name").value = data.name;
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get slide information."), "danger");
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
                    [gettext("Content"), `${data.children_count || 0} ${gettext("Folders")}, ${data.total_file_count || 0} ${gettext("Lectures")}`],
                    [gettext("Author"), data.author || "-"],
                    [gettext("Manager"), data.manager || "-"],
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

    document.getElementById("lecture-detail-modal").addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        const listElement = document.getElementById("lecture-detail-list");

        drfRequest({
            url: button.dataset.url,
            onSuccess: (data) => {
                listElement.innerHTML = "";

                const groups = document.createElement("div");
                data.viewer_group_names.forEach(group => {
                    const name = document.createElement("span");
                    name.textContent = group;
                    name.className = "badge text-bg-light border border-dark me-2";
                    groups.append(name);
                });

                const details = new Map([
                    [gettext("Name"), data.name || "-"],
                    [gettext("Description"), data.description || "-"],
                    [gettext("Content"), `${data.image_count || 0} ${gettext("Images")}`],
                    [gettext("Author"), data.author || "-"],
                    [gettext("Manager"), data.manager || "-"],
                    [gettext("Folder"), data.folder_name || "-"],
                    [gettext("Status"), data.is_open ? gettext("Open") : gettext("Closed")],
                    [gettext("Viewer Groups"), groups],
                    [pgettext("date", "Created"), formatDate(data.created_at) || "-"],
                    [pgettext("date", "Updated"), formatDate(data.updated_at) || "-"],
                ]);
                populateDetailList(listElement, details);
            },
            onError: (error) => {
                showFeedback(gettext("Failed to get lecture details."), "danger");
            },
        });
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
                const usersContainer = this.querySelector(".users-container");
                usersContainer.innerHTML = "";
                if (data.length === 0) {
                    const alert = document.createElement("div");
                    alert.classList.add("alert", "alert-warning", "mt-3");
                    alert.role = "alert";
                    alert.textContent = gettext("No users available.");
                    usersContainer.appendChild(alert);
                    return;
                }

                const groupUl = document.createElement("ul");
                groupUl.className = "list-unstyled mb-0";

                data.forEach(group => {
                    const groupLi = document.createElement("li");

                    const collapseIcon = document.createElement("i");
                    collapseIcon.className = "bi bi-chevron-right me-2 text-muted";
                    collapseIcon.dataset.bsToggle = "collapse";
                    collapseIcon.setAttribute("href", "#collapse-" + group.id);
                    collapseIcon.role = "button";

                    const groupIcon = document.createElement("i");
                    groupIcon.className = "bi bi-folder text-warning me-2";

                    const title = document.createElement("span");
                    title.textContent = group.name;

                    const userUlContainer = document.createElement("div");
                    userUlContainer.className = "collapse";
                    userUlContainer.id = "collapse-" + group.id;
                    userUlContainer.addEventListener("show.bs.collapse", function (event) {
                        event.stopPropagation();
                        collapseIcon.classList.remove("bi-chevron-right");
                        collapseIcon.classList.add("bi-chevron-down");
                    });
                    userUlContainer.addEventListener("hide.bs.collapse", function (event) {
                        event.stopPropagation();
                        collapseIcon.classList.remove("bi-chevron-down");
                        collapseIcon.classList.add("bi-chevron-right");
                    });

                    const userUl = document.createElement("ul");
                    userUl.className = "list-unstyled ms-4";
                    group.users.forEach(user => {
                        const userLi = document.createElement("li");

                        const input = document.createElement("input");
                        input.className = "form-check-input me-2";
                        input.type = "radio";
                        input.id = `user-${user.id}`;
                        input.name = "target";
                        input.value = user.id;
                        input.required = true;
                        input.disabled = user.id.toString() === sendForm.dataset.managerId;

                        const label = document.createElement("label");
                        label.className = "form-check-label";
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
                showFeedback(gettext("Failed to get users."), "danger");
            },
        });
    });

    handleModalShow("folder-rename-modal", "folder-rename-form");
    handleModalShow("folder-delete-modal", "folder-delete-form");
    handleModalShow("lecture-delete-modal", "lecture-delete-form");

    handleMoveModalShow("folder-move-modal", "folder-move-form", "folder");
    handleMoveModalShow("lecture-move-modal", "lecture-move-form", "file");

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
            url: API_ROUTES.lectureFolders.list.tree,
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
                const icon = document.createElement("i");
                icon.className = "bi bi-journal-text text-primary ps-1 me-2";
                icon.style.width = "25px";
                listItem.append(icon);
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
            },
        });
    });

});

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
                    url = API_ROUTES.lectureFolders.detail(currentItem.id).base;
                    method = "PATCH";
                    data = {parent: parseInt(destinationId)};
                } else if (currentItem.type === "lecture") {
                    url = API_ROUTES.lectures.detail(currentItem.id).base;
                    method = "PATCH";
                    data = {folder: parseInt(destinationId)};
                }
            } else if (actionType === "delete") {
                if (currentItem.type === "folder") {
                    url = API_ROUTES.lectureFolders.detail(currentItem.id).base;
                    method = "DELETE";
                } else if (currentItem.type === "slide") {
                    url = API_ROUTES.lectures.detail(currentItem.id).base;
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
