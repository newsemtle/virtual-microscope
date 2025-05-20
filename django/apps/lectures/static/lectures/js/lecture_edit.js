document.addEventListener("DOMContentLoaded", function () {

    for (content of contents) {
        const slideId = content.slide.id;
        const slideName = content.slide.name;
        const annotation = content.annotation || {};
        renderContent(slideId, slideName, annotation, content.id);
    }

    const databaseList = document.getElementById("database-list");
    renderItems(databaseList, items);

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

    // annotation 선택 시 이미지 링크 변경
    document.querySelectorAll("[name='contents[][annotation]']").forEach(annotationSelect => {
        initializeAnnotationSelect(annotationSelect);
    });

    const searchForm = document.getElementById("image-search-form");
    searchForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const query = document.getElementById("image-search-input").value;
        if (!query) {
            return;
        }
        const url = API_ROUTES.slides.list.search(encodeURIComponent(query));
        await fetchImageSearchResults(url);

        const imageList = document.getElementById("image-search-result");
        imageList.querySelectorAll("li").forEach(item => {
            const addButton = document.createElement("button");
            addButton.className = "btn btn-outline-secondary";
            addButton.innerHTML = "<i class='bi bi-plus-circle'></i>";
            addButton.title = gettext("Add");
            addButton.dataset.action = "add";

            item.querySelector(".action-button-group").appendChild(addButton);

            activateTooltips(addButton);
        });

        updateSelectedImages();
    });
    searchForm.addEventListener("click", function (event) {
        const actionElement = event.target.closest("[data-action]");
        if (!actionElement) return;
        const action = actionElement.dataset.action;

        const listItem = actionElement.closest("li");

        if (action === "add") {
            event.preventDefault();
            addContent(listItem);
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

    updateContentsOrder();
}

function removeContent(listItem) {
    if (!listItem) return;
    hideTooltips(...listItem.querySelectorAll("[data-bs-tooltip='true']"));
    listItem.remove();
    updateSelectedImages();
}

function initializeAnnotationSelect(selectItem) {
    const listItem = selectItem.closest("li");
    const slideId = getContentSlideId(listItem);
    selectItem.addEventListener("change", function (event) {
        const imageLink = listItem.querySelector(".image-link");
        imageLink.href = `/viewer/${slideId}/`;
        if (selectItem.value) {
            imageLink.href += `?annotation=${selectItem.value}`;
        }
    });
}

function loadSlideAnnotations(selectItem) {
    const listItem = selectItem.closest("li");
    const slideId = getContentSlideId(listItem);
    drfRequest({
        url: API_ROUTES.slides.detail(slideId).annotations,
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
                    const annotation = document.createElement("option");
                    annotation.value = item.id;
                    annotation.textContent = `${item.name} (${item.author})`;
                    selectItem.appendChild(annotation);
                }
            });
        },
        onError: (error) => {
            showFeedback(gettext("Failed to get slide annotations."), "danger");
        },
    });
}

function collapseFolder(listItem) {
    const folderId = listItem.dataset.folderId;
    const collapseId = `collapse-${folderId}`;
    if (document.getElementById(collapseId)) return;

    const ulChildContainer = document.createElement("div");
    ulChildContainer.className = "collapse";
    ulChildContainer.id = collapseId;
    listItem.appendChild(ulChildContainer);

    const chevronIcon = listItem.querySelector("[data-action='collapse']");
    ulChildContainer.addEventListener("show.bs.collapse", function (event) {
        event.stopPropagation();
        chevronIcon.classList.remove("bi-chevron-right");
        chevronIcon.classList.add("bi-chevron-down");
    });
    ulChildContainer.addEventListener("hide.bs.collapse", function (event) {
        event.stopPropagation();
        chevronIcon.classList.remove("bi-chevron-down");
        chevronIcon.classList.add("bi-chevron-right");
    });

    const ulChild = document.createElement("ul");
    ulChild.className = "list-group mt-2 ms-2";
    ulChildContainer.appendChild(ulChild);

    drfRequest({
        url: API_ROUTES.imageFolders.detail(folderId).items,
        onSuccess: (data) => {
            renderItems(ulChild, data);
            bootstrap.Collapse.getOrCreateInstance(ulChildContainer).show();
            updateSelectedImages();
        },
        onError: (error) => {
            showFeedback(gettext("Failed to get folder content."), "danger");
        },
    });
}

function renderItems(listElement, data) {
    const {children, slides} = data;
    if ((!children || children.length === 0) && (!slides || slides.length === 0)) {
        const noItems = document.createElement("li");
        noItems.className = "list-group-item";
        noItems.textContent = `(${gettext("No items")})`;
        listElement.appendChild(noItems);
    } else {
        children?.forEach(item => {
            const listItem = document.createElement("li");
            listItem.className = "list-group-item";
            listItem.dataset.folderId = item.id;
            listItem.dataset.folderName = item.name;
            listElement.appendChild(listItem);

            const collapseIcon = document.createElement("i");
            collapseIcon.className = "bi bi-chevron-right me-2";
            collapseIcon.setAttribute("data-bs-toggle", "collapse");
            collapseIcon.setAttribute("href", `#collapse-${item.id}`);
            collapseIcon.role = "button";
            collapseIcon.dataset.action = "collapse";

            const folderIcon = document.createElement("i");
            folderIcon.className = "bi bi-folder text-warning me-2";

            const text = document.createElement("span");
            text.textContent = item.name;

            listItem.append(collapseIcon, folderIcon, text);
        });
        slides?.forEach(item => {
            const listItem = document.createElement("li");
            listItem.className = "list-group-item";
            listItem.dataset.slideId = item.id;
            listItem.dataset.slideName = item.name;
            listElement.appendChild(listItem);

            const addIcon = document.createElement("i");
            addIcon.className = "bi bi-plus-circle me-2";
            addIcon.role = "button";
            addIcon.title = "Add";
            addIcon.dataset.bsTooltip = "true";
            addIcon.dataset.action = "add";

            const img = document.createElement("img");
            img.src = API_ROUTES.slides.detail(item.id).thumbnail;
            img.height = 40;
            img.className = "me-2";
            img.alt = "";

            const text = document.createElement("a");
            text.href = `/viewer/${item.id}/`;
            text.className = "text-decoration-none text-body";
            text.textContent = item.name;
            text.target = "_blank";
            text.rel = "noopener noreferrer nofollow";

            listItem.append(addIcon, img, text);
        });

        activateTooltips(...listElement.querySelectorAll("[data-bs-tooltip='true']"));
    }
}

function addContent(listItem) {
    const contentList = document.getElementById("content-list");
    const slideId = listItem.dataset.slideId;
    const slideName = listItem.dataset.slideName;

    const existingSlides = Array.from(contentList.querySelectorAll("li")).map(item => getContentSlideId(item));
    if (existingSlides.some(slideIdInList => slideIdInList === slideId.toString())) {
        showFeedback(interpolate(gettext("Slide '%(name)s' is already added!"), {name: slideName}, true), "warning");
        return;
    }

    renderContent(slideId, slideName);

    updateSelectedImages();
    updateContentsOrder();
}

function renderContent(slideId, slideName, annotation = {}, contentId = null) {
    const contentList = document.getElementById("content-list");

    const content = document.createElement("li");
    content.className = "list-group-item";
    content.dataset.contentId = slideId;
    contentList.appendChild(content);

    const row = document.createElement("div");
    row.className = "row g-2";
    content.appendChild(row);

    const col1 = document.createElement("div");
    col1.className = "col-md-8 d-flex gap-2 align-items-center";

    const col2 = document.createElement("div");
    col2.className = "col-md-4 d-flex gap-2 align-items-center justify-content-end ps-md-0 ps-5";

    row.append(col1, col2);

    const orderInput = document.createElement("input");
    orderInput.type = "hidden";
    orderInput.name = "contents[][order]";

    const slideInput = document.createElement("input");
    slideInput.type = "hidden";
    slideInput.name = "contents[][slide]";
    slideInput.value = slideId;

    const order = document.createElement("span");
    order.className = "bg-secondary-subtle rounded content-list-order";

    const moveContainer = document.createElement("div");
    moveContainer.className = "d-flex flex-column";

    const upBtn = document.createElement("i");
    upBtn.className = "bi bi-caret-up";
    upBtn.role = "button";
    upBtn.dataset.action = "up";

    const downBtn = document.createElement("i");
    downBtn.className = "bi bi-caret-down";
    downBtn.role = "button";
    downBtn.dataset.action = "down";

    moveContainer.append(upBtn, downBtn);

    const img = document.createElement("img");
    img.src = API_ROUTES.slides.detail(slideId).thumbnail;
    img.height = 50;
    img.alt = "";

    const slideText = document.createElement("a");
    slideText.href = `/viewer/${slideId}/`;
    slideText.className = "text-decoration-none text-body image-link";
    slideText.textContent = slideName;
    slideText.target = "_blank";
    slideText.rel = "noopener noreferrer nofollow";

    col1.append(orderInput, slideInput, order, moveContainer, img, slideText);

    const annotationLabel = document.createElement("label");
    annotationLabel.className = "text-nowrap";
    annotationLabel.textContent = gettext("Annotation");
    annotationLabel.htmlFor = `annotation-for-${slideId}`;

    const annotationSelect = document.createElement("select");
    annotationSelect.className = "form-select";
    annotationSelect.id = `annotation-for-${slideId}`;
    annotationSelect.name = "contents[][annotation]";
    annotationSelect.dataset.action = "loadAnnotation";

    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = `(${gettext("None")})`;
    defaultOption.selected = true;
    annotationSelect.appendChild(defaultOption);

    if (annotation.length > 0) {
        defaultOption.selected = false;
        const annotationOption = document.createElement("option");
        annotationOption.value = annotation.id;
        annotationOption.textContent = `${annotation.name} (${annotation.author})`;
        annotationOption.selected = true;
        annotationSelect.appendChild(annotationOption);
    }

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn btn-sm";
    removeBtn.title = gettext("Remove");
    removeBtn.dataset.bsTooltip = "tooltip";
    removeBtn.dataset.action = "remove";
    removeBtn.innerHTML = "<i class='bi bi-trash3'></i>";

    col2.append(annotationLabel, annotationSelect, removeBtn);

    initializeAnnotationSelect(annotationSelect);
    activateTooltips(removeBtn);
}

function submitChanges(formItem) {
    const formData = new FormData(formItem);

    let data = {
        name: formData.get("name"),
        description: formData.get("description"),
        viewer_groups: formData.getAll("viewer_groups[]").map(id => parseInt(id.toString(), 10)),
        contents: [],
    };

    document.querySelectorAll("#content-list li").forEach((item, index) => {
        const orderInput = item.querySelector("[name='contents[][order]']");
        const slideInput = item.querySelector("[name='contents[][slide]']");
        const annotationInput = item.querySelector("[name='contents[][annotation]']");

        const orderValue = orderInput.value;
        const slideValue = slideInput.value;
        if (!slideValue || !orderValue) {
            showFeedback(gettext("Error occurred."), "danger");
            return;
        }
        const annotationValue = annotationInput?.value;

        data.contents.push({
            id: item.dataset.contentId || null,
            order: parseInt(orderValue, 10),
            slide: parseInt(slideValue, 10),
            annotation: annotationValue ? parseInt(annotationValue, 10) : null,
        });
    });

    drfRequest({
        url: formItem.dataset.url,
        method: formItem.dataset.method,
        data: data,
        onSuccess: (data) => {
            sendFeedback(interpolate(gettext("Lecture '%(name)s' updated successfully!"), {name: data.name}, true), "success");
            redirectToNextOrDefault(`/lectures/database/?folder=${data.folder}`);
        },
        onError: (error) => {
            showFeedback(gettext("Failed to update lecture."), "danger");
        },
    });
}

function updateContentsOrder() {
    const items = document.querySelectorAll("#content-list li");
    for (let i = 0; i < items.length; i++) {
        items[i].querySelector("[name='contents[][order]']").value = (i + 1).toString();
        items[i].querySelector(".content-list-order").textContent = (i + 1).toString();
    }
}

function updateSelectedImages() {
    const contentSlideList = Array.from(document.getElementById("content-list").querySelectorAll("[name='contents[][slide]']"));
    const selectedImages = contentSlideList.map(item => parseInt(item.value, 10));

    const databaseList = Array.from(document.getElementById("database-list").querySelectorAll("li"));
    databaseList.forEach(item => {
        if (item.dataset.slideId === undefined) return;

        const slideId = parseInt(item.dataset.slideId, 10);

        if (selectedImages.includes(slideId)) {
            item.classList.add("opacity-50");
            item.classList.add("bg-secondary-subtle");
        } else {
            item.classList.remove("opacity-50");
            item.classList.remove("bg-secondary-subtle");
        }
    });

    const imageList = document.getElementById("image-search-result");
    imageList.querySelectorAll("li").forEach(item => {
        const slideId = parseInt(item.dataset.slideId, 10);

        if (selectedImages.includes(slideId)) {
            item.classList.add("opacity-50");
            item.classList.add("bg-secondary-subtle");
        } else {
            item.classList.remove("opacity-50");
            item.classList.remove("bg-secondary-subtle");
        }
    });
}

function getContentSlideId(listItem) {
    const slideInput = listItem.querySelector("[name='contents[][slide]']");
    return slideInput?.value || null;
}