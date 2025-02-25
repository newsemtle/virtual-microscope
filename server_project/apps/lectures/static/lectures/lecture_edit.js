document.addEventListener("DOMContentLoaded", function () {
    const lectureForm = document.getElementById("lecture-form");
    const databaseList = document.getElementById("database-list");

    lectureForm.addEventListener("click", function (event) {
        const actionElement = event.target.closest("[data-action]");
        if (!actionElement) return;

        const action = actionElement.dataset.action;
        const listItem = actionElement.closest("li");

        if (action === "up" || action === "down") {
            moveContent(listItem, action);
        } else if (action === "remove") {
            removeContent(listItem);
        } else if (action === "loadAnnotation") {
            setupSlideAnnotation(actionElement);
        }
    });

    lectureForm.addEventListener("submit", function (event) {
        event.preventDefault();
        submitChanges(this);
    });

    databaseList.addEventListener("click", function (event) {
        const actionElement = event.target.closest("[data-action]");
        if (!actionElement) return;

        const action = actionElement.dataset.action;
        const listItem = actionElement.closest("li");

        if (action === "add") {
            addContent(listItem);
        } else if (action === "collapse") {
            collapseFolder(listItem);
        }
    });
});


function moveContent(listItem, direction) {
    if (!listItem) return;

    const parent = listItem.parentNode;
    if (direction === "up") {
        const prevItem = listItem.previousElementSibling;
        if (prevItem) parent.insertBefore(listItem, prevItem);
    } else if (direction === "down") {
        const nextItem = listItem.nextElementSibling;
        if (nextItem) parent.insertBefore(nextItem, listItem);
    }
}

function removeContent(listItem) {
    if (!listItem) return;
    listItem.remove();
}

function setupSlideAnnotation(selectItem) {

    fetch(selectItem.dataset.url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
        },
    })
        .then(response => {
            console.log(response)
            if (!response.ok) {
                return response.json().then(errorData => {
                    console.error('Error fetching slide annotations:', errorData.details);
                    throw new Error('Failed to fetch annotations');
                });
            }
            return response.json();
        })
        .then(data => {
            if (!data || data.length === 0) return;

            const existingOptions = new Set(Array.from(selectItem.options).map(option => option.value));

            Array.from(selectItem.options).forEach(option => {
                if (!data.some(item => item.id.toString() === option.value) && option.value) {
                    selectItem.removeChild(option);
                }   
            });

            data.forEach(item => {
                if (!existingOptions.has(item.id.toString())) {
                    const annotation = document.createElement('option');
                    annotation.value = item.id;
                    annotation.textContent = `${item.name} - ${item.author}`;
                    selectItem.appendChild(annotation);
                }
            });
        })
        .catch(error => {
            console.error('Error fetching slide annotations:', error.message);
            showFeedback(error.message, "danger");
        });
}

function collapseFolder(listItem) {
    const folderId = listItem.dataset.folderId;
    const contentId = `collapse-${folderId}`;
    let content = document.getElementById(contentId);
    const chevronIcon = listItem.querySelector('[data-action="collapse"]');

    chevronIcon.classList.toggle('bi-chevron-right');
    chevronIcon.classList.toggle('bi-chevron-down');

    if (content) return;

    content = document.createElement('ul');
    content.className = 'list-group mt-2 ms-2 collapse show';
    content.id = contentId;
    listItem.appendChild(content);

    fetch(listItem.dataset.url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
        },
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const {subfolders, slides} = data;
            if ((!subfolders || subfolders.length === 0) && (!slides || slides.length === 0)) {
                content.innerHTML = '<li class="list-group-item">(No items)</li>';
            } else {
                subfolders?.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'list-group-item';
                    listItem.dataset.url = item.url;
                    listItem.dataset.folderId = item.id;
                    listItem.dataset.folderName = item.name;

                    const chevronIcon = document.createElement('i');
                    chevronIcon.className = 'bi bi-chevron-right me-2';
                    chevronIcon.setAttribute('data-bs-toggle', 'collapse');
                    chevronIcon.setAttribute('href', `#collapse-${item.id}`);
                    chevronIcon.role = 'button';
                    chevronIcon.dataset.action = "collapse";

                    const folderIcon = document.createElement('i');
                    folderIcon.className = 'bi bi-folder text-warning me-2';

                    const text = document.createElement('span');
                    text.textContent = item.name;

                    listItem.append(chevronIcon, folderIcon, text);
                    content.appendChild(listItem);
                });

                slides?.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'list-group-item';
                    listItem.dataset.url = item.url;
                    listItem.dataset.annotationsUrl = item.annotations_url
                    listItem.dataset.slideId = item.id;
                    listItem.dataset.slideName = item.name;

                    const img = document.createElement('img');
                    img.src = item.thumbnail;
                    img.height = 40;
                    img.className = 'me-2';
                    img.alt = '';

                    const text = document.createElement('a')
                    text.href = item.view_url;
                    text.classList.add('text-decoration-none');
                    text.textContent = item.name;
                    text.target = '_blank';
                    text.rel = 'noopener noreferrer nofollow';

                    const addButton = document.createElement('button');
                    addButton.className = 'btn btn-sm';
                    addButton.title = 'Add';
                    addButton.dataset.action = 'add';

                    const icon = document.createElement('i');
                    icon.className = 'bi bi-plus-lg';

                    addButton.appendChild(icon);
                    listItem.append(img, text, addButton);
                    content.appendChild(listItem);
                });
            }
        })
        .catch(error => {
            showFeedback(error.message, "danger");
        });
}

function addContent(listItem) {
    const contentList = document.getElementById('content-list');
    const slideId = listItem.dataset.slideId;
    const slideName = listItem.dataset.slideName;

    const existingSlides = Array.from(contentList.querySelectorAll('li')).map(item => item.dataset.slideId);
    if (existingSlides.some(slideIdInList => slideIdInList === slideId.toString())) {
        showFeedback(`Slide "${slideName}" is already added!`, "warning");
        return;
    }

    const content = document.createElement('li');
    content.className = 'list-group-item d-flex align-items-center';
    content.dataset.url = listItem.dataset.url;
    content.dataset.slideId = slideId;

    const slideInput = document.createElement('input');
    slideInput.type = 'hidden';
    slideInput.name = 'contents[][slide]';
    slideInput.value = slideId;

    const moveContainer = document.createElement('div');
    moveContainer.className = 'd-flex flex-column me-2';

    const upBtn = document.createElement('i');
    upBtn.className = 'bi bi-caret-up';
    upBtn.role = 'button';
    upBtn.dataset.action = 'up';

    const downBtn = document.createElement('i');
    downBtn.className = 'bi bi-caret-down';
    downBtn.role = 'button';
    downBtn.dataset.action = 'down';

    moveContainer.append(upBtn, downBtn);

    const img = document.createElement('img');
    img.src = listItem.querySelector('img').src;
    img.height = 40;
    img.className = 'me-2';
    img.alt = '';

    const slideText = document.createElement('a');
    slideText.href = listItem.querySelector('a').href;
    slideText.classList.add('text-decoration-none');
    slideText.textContent = slideName;
    slideText.target = '_blank';
    slideText.rel = 'noopener noreferrer nofollow';

    const annotationContainer = document.createElement('div');
    annotationContainer.className = 'ms-auto col-3';

    const annotationLabel = document.createElement('label');
    annotationLabel.textContent = 'Annotation:';
    annotationLabel.htmlFor = `annotation-for-${slideId}`;

    const annotationSelect = document.createElement('select');
    annotationSelect.className = 'form-select';
    annotationSelect.id = `annotation-for-${slideId}`;
    annotationSelect.name = 'contents[][annotation]';
    annotationSelect.dataset.action = 'loadAnnotation';
    annotationSelect.dataset.url = listItem.dataset.annotationsUrl

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'None';
    defaultOption.selected = true;

    annotationSelect.appendChild(defaultOption);
    annotationContainer.append(annotationLabel, annotationSelect);

    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-sm';
    removeBtn.title = 'Remove';
    removeBtn.dataset.action = 'remove';

    const removeIcon = document.createElement('i');
    removeIcon.className = 'bi bi-trash3';

    removeBtn.appendChild(removeIcon);
    content.append(slideInput, moveContainer, img, slideText, annotationContainer, removeBtn);
    contentList.appendChild(content);
}

function submitChanges(formItem) {
    const formData = new FormData(formItem);

    let data = {
        name: formData.get("name"),
        description: formData.get("description"),
        groups: [],
        contents: []
    };

    formData.getAll("groups[]").forEach(id => {
        data.groups.push(parseInt(id.toString(), 10));
    });

    let slides = formData.getAll("contents[][slide]");
    let annotations = formData.getAll("contents[][annotation]");

    for (let i = 0; i < slides.length; i++) {
        data.contents.push({
            order: i + 1,
            slide: parseInt(slides[i].toString(), 10),
            annotation: annotations[i] ? parseInt(annotations[i].toString(), 10) : null
        });
    }

    fetch(formItem.dataset.url, {
        method: 'PATCH',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    console.error("Error updating lecture:", errorData.details);
                    throw new Error(errorData.details);
                });
            }
            return response.json();
        })
        .then(responseData => {
            showFeedback(`Lecture '${responseData.name}' updated successfully!`, "success");
        })
        .catch(error => {
            showFeedback(error.message, "danger");
        });
}
