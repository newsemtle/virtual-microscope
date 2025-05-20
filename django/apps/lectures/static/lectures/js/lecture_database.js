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

    document.getElementById("folder-detail-modal").addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
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
        const button = event.relatedTarget;
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
        const button = event.relatedTarget;
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

    handleModalShow("lecture-delete-modal", "lecture-delete-form");

    handleMoveModalShow("lecture-move-modal", "lecture-move-form", "file");

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
                image = document.createElement("i");
                image.className = "bi bi-journal-text text-primary ps-1 me-2";
                image.style.width = "25px";
            }

            const name = document.createElement("span");
            name.textContent = item.name;

            title.append(image, name);
        });

        if (button.dataset.type === "move") {
            title.textContent = gettext("Move Selected Items");
            await processBulkAction("lecture", selectedItems, "move", button.dataset.destination);
        } else if (button.dataset.type === "delete") {
            title.textContent = gettext("Delete Selected Items");
            await processBulkAction("lecture", selectedItems, "delete");
        }
        continueButton.classList.remove("btn-secondary");
        continueButton.classList.add("btn-success");
        continueButton.textContent = gettext("Close");
        unfreezeModal(this);
    });

    handleModalFormSubmit("lecture-move-form");
    handleModalFormSubmit("lecture-duplicate-form");
    handleModalFormSubmit("lecture-send-form");
    handleModalFormSubmit("lecture-delete-form");

    document.getElementById("lecture-create-form").addEventListener("submit", function (event) {
        event.preventDefault();
        submitForm({
            form: this,
            onSuccess: (data) => {
                window.location.href = `/lectures/${data.id}/edit/`;
            },
        });
    });

});