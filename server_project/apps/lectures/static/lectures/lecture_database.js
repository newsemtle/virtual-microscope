document.getElementById("renameFolderModal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;

    fetch(button.dataset.url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
        },
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    console.error('Error fetching slide infos:', errorData.details);
                    throw new Error('Failed to fetch slide infos');
                });
            }
            return response.json();
        })
        .then(data => {
            document.getElementById("renameFolderName").value = data.name;
        })
        .catch(error => {
            console.error('Error fetching slide infos:', error.message);
        });
});

document.getElementById("detailFolderModal").addEventListener("show.bs.modal", function (event) {
    let button = event.relatedTarget;

    fetch(button.dataset.url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
        },
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    console.error('Error fetching folder details:', errorData.details);
                    throw new Error('Failed to fetch folder details');
                });
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('detail-folder-name').textContent = data.name || '-';
            document.getElementById('detail-folder-contents').textContent = `${data.subfolders_count || 0} subfolders, ${data.lectures_count || 0} lectures`;
            document.getElementById('detail-folder-author').textContent = data.author || '-';
            document.getElementById('detail-folder-parent').textContent = data.parent_name || '-';
            document.getElementById('detail-folder-created').textContent = data.created_at_formatted || '-';
            document.getElementById('detail-folder-updated').textContent = data.updated_at_formatted || '-';
        })
        .catch(error => {
            console.error('Error fetching folder details:', error.message);
        });
});

function handleModalShow(modalId, formId) {
    document.getElementById(modalId).addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        document.getElementById(formId).dataset.url = button.dataset.url;
    });
}

handleModalShow("renameFolderModal", "renameFolderForm");
handleModalShow("deleteFolderModal", "deleteFolderForm");
handleModalShow("deleteLectureModal", "deleteLectureForm");

function handleMoveModalShow(modalId, formId, itemType) {
    document.getElementById(modalId).addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        document.getElementById(formId).dataset.url = button.dataset.url;

        fetch(button.dataset.urlTree, {
            method: 'GET',
            headers: {
                'X-CSRFToken': CSRF_TOKEN,
            },
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        console.error('Error fetching folder tree:', errorData.details);
                        throw new Error('Failed to fetch folder tree');
                    });
                }
                return response.json();
            })
            .then(data => {
                const treeContainer = this.querySelector('.folder-tree-container');
                treeContainer.innerHTML = '';
                if (data.length === 0) {
                    const alert = document.createElement('div');
                    alert.classList.add('alert', 'alert-warning', 'mt-3');
                    alert.role = 'alert';
                    alert.textContent = 'No folders available.';
                    treeContainer.appendChild(alert);
                    return;
                }
                treeContainer.appendChild(createTree(data, button.dataset.itemId, itemType));
            })
            .catch(error => {
                console.error('Error fetching folder tree:', error.message);
            });
    });
}

function createTree(data, itemId, type) {
    if (!["folder", "lecture"].includes(type)) return;

    const ul = document.createElement('ul');
    ul.classList.add('list-unstyled');

    data.forEach(item => {
        const selectable = type === "folder" ? item.id.toString() !== itemId : true;
        const showChildren = item.subfolders?.length > 0 && selectable;

        const li = document.createElement('li');
        li.classList.add('mb-2');

        const div = document.createElement('div');
        div.classList.add('form-check', 'mb-2');

        const input = document.createElement('input');
        input.classList.add('form-check-input');
        input.type = 'radio';
        input.id = `folder-${item.id}`;
        input.name = type === "folder" ? "parent" : "folder";
        input.value = item.id;
        input.required = true;
        input.disabled = !selectable;

        const icon = document.createElement('i');
        icon.classList.add('bi', 'bi-chevron-right', 'me-2', 'text-muted');
        icon.addEventListener('click', () => {
            if (!showChildren) return;
            icon.classList.toggle('bi-chevron-right');
            icon.classList.toggle('bi-chevron-down');
        });

        const label = document.createElement('label');
        label.classList.add('form-check-label');
        label.htmlFor = input.id;
        label.innerHTML = `<i class="bi bi-folder text-warning me-2"></i> ${item.name}`;

        let ulChild = document.createElement('ul');
        if (showChildren) {
            icon.classList.remove('text-muted');
            icon.dataset.bsToggle = 'collapse';
            icon.setAttribute('href', '#collapse-' + item.id);
            icon.role = 'button';

            ulChild = createTree(item.subfolders, itemId, type);
            ulChild.classList.add('list-unstyled', 'ms-4', 'collapse');
            ulChild.id = 'collapse-' + item.id;
        }

        div.append(input, icon, label);
        li.append(div, ulChild);
        ul.appendChild(li);
    });

    return ul;
}

handleMoveModalShow("moveFolderModal", "moveFolderForm", "folder");
handleMoveModalShow("moveLectureModal", "moveLectureForm", "lecture");

function submitForm(form, method) {
    fetch(form.dataset.url, {
        method: method,
        headers: {
            "X-CSRFToken": CSRF_TOKEN,
        },
        body: new FormData(form),
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    console.error(`Error (${method}):`, errorData.details);
                    throw new Error(`Failed to ${method.toLowerCase()} item`);
                });
            }
            location.reload();
        })
        .catch(error => {
            console.error(`Error (${method}):`, error.message);
            alert("Failed to submit the form. Please try again.");
            location.reload();
        });
}

document.getElementById("newFolderForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitForm(this, "POST");
});
document.getElementById("renameFolderForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitForm(this, "PATCH");
});
document.getElementById("moveFolderForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitForm(this, "PATCH");
});
document.getElementById("deleteFolderForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitForm(this, "DELETE");
});
document.getElementById("newLectureForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitForm(this, "POST");
});
document.getElementById("moveLectureForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitForm(this, "PATCH");
});
document.getElementById("deleteLectureForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitForm(this, "DELETE");
});