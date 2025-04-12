document.addEventListener("DOMContentLoaded", function () {
    updateSelectedImages();

    const lectureForm = document.getElementById("lecture-form");

    lectureForm.addEventListener("submit", function (event) {
        event.preventDefault();
        submitChanges(this);
    });

    lectureForm.addEventListener("click", function (event) {
        const actionElement = event.target.closest("[data-action]");
        if (!actionElement) return;
        const action = actionElement.dataset.action;

        const listItem = actionElement.closest("li");

        if (action === "up" || action === "down") {
            event.preventDefault();
            moveContent(listItem, action);
        } else if (action === "remove") {
            event.preventDefault();
            removeContent(listItem);
        } else if (action === "add") {
            event.preventDefault();
            addContent(listItem);
        } else if (action === "collapse") {
            event.preventDefault();
            collapseFolder(listItem);
        }
    });

    lectureForm.addEventListener("mousedown", function (event) {
        const actionElement = event.target.closest("[data-action]");
        if (!actionElement) return;
        const action = actionElement.dataset.action;

        if (action === "loadAnnotation") {
            actionElement.disabled = true;
            loadSlideAnnotations(actionElement);
            actionElement.disabled = false;
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
    updateSelectedImages();
}

function loadSlideAnnotations(selectItem) {
    fetchData({
        url: selectItem.dataset.url,
        onSuccess: (data) => {
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
                    annotation.textContent = `${item.name} (${item.author})`;
                    selectItem.appendChild(annotation);
                }
            });
        },
        onError: (error) => {
            showFeedback("Error loading slide annotations: " + error.message, "danger");
        }
    })
}

function collapseFolder(listItem) {
    const collapseId = `collapse-${listItem.dataset.folderId}`;
    if (document.getElementById(collapseId)) return;

    const ulChildContainer = document.createElement('div');
    ulChildContainer.className = 'collapse';
    ulChildContainer.id = collapseId;

    const chevronIcon = listItem.querySelector('[data-action="collapse"]');
    ulChildContainer.addEventListener('show.bs.collapse', function (event) {
        event.stopPropagation();
        chevronIcon.classList.remove('bi-chevron-right');
        chevronIcon.classList.add('bi-chevron-down');
    });
    ulChildContainer.addEventListener('hide.bs.collapse', function (event) {
        event.stopPropagation();
        chevronIcon.classList.remove('bi-chevron-down');
        chevronIcon.classList.add('bi-chevron-right');
    });

    const ulChild = document.createElement('ul');
    ulChild.className = 'list-group mt-2 ms-2';

    fetchData({
        url: listItem.dataset.url,
        onSuccess: (data) => {
            const {subfolders, slides} = data;
            if ((!subfolders || subfolders.length === 0) && (!slides || slides.length === 0)) {
                ulChild.innerHTML = '<li class="list-group-item">(No items)</li>';
            } else {
                subfolders?.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'list-group-item';
                    listItem.dataset.url = item.url;
                    listItem.dataset.folderId = item.id;
                    listItem.dataset.folderName = item.name;

                    const collapseIcon = document.createElement('i');
                    collapseIcon.className = 'bi bi-chevron-right me-2';
                    collapseIcon.setAttribute('data-bs-toggle', 'collapse');
                    collapseIcon.setAttribute('href', `#collapse-${item.id}`);
                    collapseIcon.role = 'button';
                    collapseIcon.dataset.action = "collapse";

                    const folderIcon = document.createElement('i');
                    folderIcon.className = 'bi bi-folder text-warning me-2';

                    const text = document.createElement('span');
                    text.textContent = item.name;

                    listItem.append(collapseIcon, folderIcon, text);
                    ulChild.appendChild(listItem);
                });

                slides?.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'list-group-item';
                    listItem.dataset.annotationsUrl = item.annotations_url
                    listItem.dataset.slideId = item.id;
                    listItem.dataset.slideName = item.name;

                    const addIcon = document.createElement('i');
                    addIcon.className = 'bi bi-plus-circle me-2';
                    addIcon.role = 'button';
                    addIcon.setAttribute('data-bs-tooltip', 'tooltip')
                    addIcon.title = 'Add';
                    addIcon.dataset.action = 'add';

                    const img = document.createElement('img');
                    img.src = item.thumbnail;
                    img.height = 40;
                    img.className = 'me-2';
                    img.alt = '';

                    const text = document.createElement('a')
                    text.href = item.view_url;
                    text.className = 'text-decoration-none text-body';
                    text.textContent = item.name;
                    text.target = '_blank';
                    text.rel = 'noopener noreferrer nofollow';

                    listItem.append(addIcon, img, text);
                    ulChild.appendChild(listItem);
                });
            }

            ulChildContainer.appendChild(ulChild);
            listItem.appendChild(ulChildContainer);

            activateTooltips();
            $(ulChildContainer).collapse('show');

            updateSelectedImages();
        },
        onError: (error) => {
            showFeedback("Error loading folder content: " + error.message, "danger");
        }
    })
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
    slideText.className = 'text-decoration-none text-body';
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

    updateSelectedImages();
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

    fetchData({
        url: formItem.dataset.url,
        method: 'PATCH',
        data: data,
        onSuccess: (data) => {
            sendFeedback(`Lecture '${data.name}' updated successfully!`, "success")
            localStorage.setItem("refreshPage", "true");
            window.close();
        },
        onError: (error) => {
            showFeedback("Error updating lecture: " + error.message, "danger");
        }
    })
}

function updateSelectedImages() {
    const contentList = Array.from(document.getElementById('content-list').querySelectorAll('li'));
    const selectedImages = contentList.map(item => parseInt(item.dataset.slideId, 10));

    const databaseList = Array.from(document.getElementById('database-list').querySelectorAll('li'));
    databaseList.forEach(item => {
        if (item.dataset.slideId === undefined) return;

        const slideId = parseInt(item.dataset.slideId, 10);

        if (selectedImages.includes(slideId)) {
            item.classList.add('opacity-50')
            item.classList.add('bg-secondary-subtle')
        } else {
            item.classList.remove('opacity-50');
            item.classList.remove('bg-secondary-subtle');
        }
    });
}