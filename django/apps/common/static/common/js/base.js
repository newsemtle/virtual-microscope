document.addEventListener('DOMContentLoaded', () => {

    loadFeedback();
    activateTooltips();

    const logoutElement = document.getElementById('logout');
    logoutElement?.addEventListener("click", function (event) {
        drfRequest({
            url: this.dataset.url,
            method: "POST",
            onSuccess: (data) => {
                window.location.href = '/';
            },
            onError: (error) => {
                showFeedback(`Failed to logout: ${error}`, "danger");
            }
        });
    });

    const sessionTimeElement = document.getElementById('session-time')
    if (sessionTimeElement) {
        let timer = new Timer('session-time');
        let lastFetchTime = 0;
        const throttleDuration = 2000;
        sessionTimeElement.addEventListener("click", function (event) {
            const now = Date.now();
            if (now - lastFetchTime < throttleDuration) {
                return;
            }
            lastFetchTime = now;
            drfRequest({
                url: this.dataset.url,
                method: "POST",
                onSuccess: (data) => {
                    timer.start(new Date(data.expire) - Date.now());
                },
                onError: (error) => {
                    showFeedback(`Failed to fetch session time: ${error}`, "danger");
                }
            });
        });
        sessionTimeElement.click();
    }

    document.querySelectorAll('.modal')?.forEach(modalElement => {
        modalElement.addEventListener('hidden.bs.modal', () => {
            unfreezeModal(modalElement);
            const forms = modalElement.querySelectorAll('form');
            [...forms].forEach(form => {
                form.reset();
                clearFormErrors(form);
            });
        });
    });

    document.getElementById('item-checkbox-all')?.addEventListener('click', function (event) {
        const checkboxes = document.querySelectorAll('[name="item-checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    })

    document.querySelectorAll('[name="item-checkbox"]')?.forEach((checkbox) => {
        checkbox.addEventListener('click', function (event) {
            const checkboxes = document.querySelectorAll('[name="item-checkbox"]');
            document.getElementById('item-checkbox-all').checked = [...checkboxes].every(checkbox => checkbox.checked);
        });
    })

});

class Timer {
    constructor(timeElementId) {
        this.timer = null;
        this.element = document.getElementById(timeElementId);
        this.timeRemaining = 0;
        this.originalTime = 0;
    }

    start(timeInMs) {
        this.stop();

        this.originalTime = timeInMs;
        this.timeRemaining = timeInMs;

        const update = () => {
            if (this.timeRemaining < 0) {
                this.stop();
                return;
            }

            const seconds = Math.floor(this.timeRemaining / 1000);
            const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
            const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
            const s = String(seconds % 60).padStart(2, '0');

            this.element.textContent = `${h}:${m}:${s}`;
            this.timeRemaining -= 1000;
        };

        update();
        this.timer = setInterval(update, 1000);
    }

    stop() {
        if (this.timer) {
            clearInterval(this.timer);
        }
    }

    reset() {
        this.stop();
        this.start(this.originalTime);
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getQueryParam(key, url = window.location.href) {
    const searchParams = new URL(url).searchParams;
    return searchParams.get(key);
}

function activateTooltips(element = null) {
    let tooltipTriggerList;
    if (element) {
        tooltipTriggerList = [element];
    } else {
        tooltipTriggerList = document.querySelectorAll('[data-bs-tooltip="tooltip"]');
    }
    [...tooltipTriggerList].forEach(tooltipTriggerEl => {
        new bootstrap.Tooltip(tooltipTriggerEl, {trigger: 'hover', delay: {"show": 500}});
    });
}

function loadFeedback() {
    let feedbackData = JSON.parse(localStorage.getItem("feedbackData"));
    if (feedbackData && feedbackData.length > 0) {
        feedbackData.forEach(feedback => {
            showFeedback(feedback.text, feedback.type);
        });
        localStorage.removeItem("feedbackData");
    }
}

function freezeModal(modalElement) {
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal._config.keyboard = false;
    modal._config.backdrop = 'static';

    modalElement.querySelectorAll('button').forEach(button => {
        button.disabled = true;
    });
}

function unfreezeModal(modalElement) {
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal._config.keyboard = true;
    modal._config.backdrop = true;

    modalElement.querySelectorAll('button').forEach(button => {
        button.disabled = false;
    });
}

function handleFormErrors(form, error) {
    clearFormErrors(form);

    const message = form.querySelector(`[data-type="message"]`);
    if (message) {
        message.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${error.message}`;
        message.classList.remove('d-none');
    }

    if (error.fieldErrors) {
        for (const [field, message] of Object.entries(error.fieldErrors)) {
            const input = form.querySelector(`#${field}`);
            if (input) {
                input.classList.add('is-invalid');
            }
            const feedback = form.querySelector(`#${field}-feedback`);
            if (feedback) {
                feedback.textContent = message;
            }
        }
    }
}

function clearFormErrors(formElement) {
    formElement.classList.remove('was-validated');
    formElement.querySelectorAll('.is-invalid').forEach((input) => {
        input.classList.remove('is-invalid');
    });
    formElement.querySelectorAll('.invalid-feedback').forEach((feedback) => {
        feedback.textContent = '';
    });
    formElement.querySelectorAll('[data-type="message"]').forEach((message) => {
        message.classList.add('d-none');
        message.innerHTML = '';
    });
}

function handleModalFormSubmit(formId) {
    document.getElementById(formId).addEventListener("submit", function (event) {
        event.preventDefault();
        submitForm({
            form: this,
            onSuccess: (data) => {
                location.reload();
            }
        });
    });
}

function handleModalShow(modalId, formId) {
    document.getElementById(modalId).addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        document.getElementById(formId).dataset.url = button.dataset.url;
    });
}

function handleMoveModalShow(modalId, formId, itemType) {
    document.getElementById(modalId).addEventListener("show.bs.modal", function (event) {
        let button = event.relatedTarget;
        document.getElementById(formId).dataset.url = button.dataset.url;

        drfRequest({
            url: button.dataset.urlTree,
            onSuccess: (data) => {
                const treeContainer = this.querySelector('.folder-tree-container');
                renderMoveTree(treeContainer, data, itemType, [button.dataset.itemId]);
            },
            onError: (error) => {
                showFeedback('Error fetching folder tree: ' + error.message, 'danger');
            }
        });
    });
}

function renderMoveTree(container, data, itemType, movingFolderIds) {
    container.innerHTML = '';
    if (data.length === 0) {
        const alert = document.createElement('div');
        alert.classList.add('alert', 'alert-warning', 'mt-3');
        alert.role = 'alert';
        alert.textContent = 'No folders available.';
        container.appendChild(alert);
        return;
    }
    if (itemType === "folder") {
        container.appendChild(createMoveTree(data, itemType, movingFolderIds));
    } else {
        container.appendChild(createMoveTree(data, itemType));
    }
}

/**
 * Displays a feedback message on the screen. The message will appear in a styled alert box
 * and automatically disappears after a specified timeout.
 *
 * @param {string} message - The feedback message to be displayed.
 * @param {string} [type="info"] - The type of feedback message, which determines its style.
 *                                  Possible values include "info", "success", "warning", or "danger".
 * @return {void} This function does not return a value.
 */
function showFeedback(message, type = "info") {
    let feedbackContainer = document.getElementById("feedback-container");

    if (!feedbackContainer) {
        feedbackContainer = document.createElement("div");
        feedbackContainer.id = "feedback-container";
        feedbackContainer.className = "position-fixed top-0 start-50 translate-middle-x mt-3 d-flex flex-column align-items-center";
        feedbackContainer.style.zIndex = "1100";
        document.body.appendChild(feedbackContainer);
    }

    const feedbackDiv = document.createElement("div");
    feedbackDiv.className = `alert alert-${type} p-2 mb-2`;
    feedbackDiv.textContent = message;

    feedbackContainer.appendChild(feedbackDiv);

    setTimeout(() => {
        feedbackDiv.remove();
        if (feedbackContainer.children.length === 0) {
            feedbackContainer.remove();
        }
    }, 5000);
}

/**
 * Sends feedback by storing the message and its type in the local storage.
 *
 * @param {string} message - The feedback message to be stored.
 * @param {string} [type="info"] - The type of feedback message, which determines its style.
 *                                  Possible values include "info", "success", "warning", or "danger".
 * @return {void} This function does not return a value.
 */
function sendFeedback(message, type = "info") {
    let feedbackData = JSON.parse(localStorage.getItem("feedbackData")) || [];
    feedbackData.push({text: message, type: type});
    localStorage.setItem("feedbackData", JSON.stringify(feedbackData));
}

/**
 * Sends an HTTP request using the Fetch API with support for CSRF tokens and custom handling of success and error responses.
 *
 * @param {Object} options - The options for the request.
 * @param {string} options.url - The URL to which the request is sent.
 * @param {string} [options.method='GET'] - The HTTP request method (e.g., GET, POST, PUT, DELETE).
 * @param {Object} [options.headers={}] - Additional headers to be sent with the request.
 * @param {FormData|Object|string|null} [options.data=null] - The request payload. Can be FormData, an object, a string, or null.
 * @param {Function} [options.onSuccess=() => {}] - Callback function executed when the request succeeds. The response data is passed as a parameter.
 * @param {Function} [options.onError=() => {}] - Callback function executed when the request fails. The error object is passed as a parameter.
 * @return {void} No return value. Handles the request internally and executes the appropriate callback.
 */
async function drfRequest({
                              url,
                              method = 'GET',
                              headers = {},
                              data = null,
                              onSuccess = () => {
                              },
                              onError = () => {
                              },
                              onNext: onFinally = () => {
                              }
                          }) {
    const options = {method, headers};
    options.headers['X-CSRFToken'] = getCookie('csrftoken');
    options.headers['Accept-Language'] = navigator.language;

    if (data) {
        if (data instanceof FormData) {
            if ([...data.entries()].length !== 0) {
                options.body = data;
            }
        } else if (typeof data === 'object') {
            options.body = JSON.stringify(data);
            options.headers['Content-Type'] = 'application/json';
        } else {
            options.body = data;
        }
    }

    return fetch(url, options)
        .then(async response => {
            const status = response.status;

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch {
                    errorData = {detail: `API Error (status ${status})`};
                }

                const classified = classifyError(errorData, status);
                throw {...classified, status, raw: errorData};
            }

            return status === 204 ? null : response.json();
        })
        .then(data => onSuccess(data))
        .catch(error => {
            console.log(error);
            onError(error);
        })
        .finally(() => onFinally());
}

/**
 * Submits a form by sending a request using the specified method and handles success or error callbacks.
 *
 * @param {Object} options - The options for the form submission.
 * @param {HTMLFormElement} options.form - The form element to be submitted.
 * @param {Function} [options.onSuccess] - Optional callback function to execute on a successful request.
 * @param {Function} [options.onError] - Optional callback function to execute if an error occurs during the request.
 * @return {void} This method does not return a value.
 */
function submitForm({
                        form,
                        onSuccess = () => {
                        },
                        onError = () => {
                        }
                    }) {
    if (form.checkValidity()) {
        form.classList.remove('was-validated');
    } else {
        form.classList.add('was-validated');
        form.querySelector('[data-type="message"]').classList.add('d-none');
        form.querySelectorAll('.invalid-feedback').forEach((feedback) => {
            feedback.textContent = 'This field is required.';
        })
        onError({message: 'Validation error'});
        return;
    }
    drfRequest({
        url: form.dataset.url,
        method: form.dataset.method,
        data: new FormData(form),
        onSuccess: onSuccess,
        onError: (error) => {
            handleFormErrors(form, error);
            onError(error);
        }
    })
}

/**
 * Populates a definition list (`<dl>`) element with key-value pairs from a details object.
 *
 * @param {HTMLDListElement} dl - The definition list element to populate.
 * @param {Object} details - An object containing key-value pairs to display in the definition list.
 * @return {void} Does not return a value.
 */
function createDetailList(dl, details) {
    for (const [key, value] of Object.entries(details)) {
        const dt = document.createElement('dt');
        dt.className = 'col-sm-3';
        dt.textContent = key;
        const dd = document.createElement('dd');
        dd.className = 'col-sm-9';
        dd.innerHTML = value;
        dl.append(dt, dd);
    }
}

/**
 * Creates a nested move tree structure in the form of an unordered list (ul) element.
 * This structure is used to display and manage tree-like data with selectable items for moving folders or files.
 *
 * @param {Array} data - An array of objects representing the items (folders or files) to populate the tree structure. Each object should contain `id`, `name`, and an optional `children` array.
 * @param {string} itemType - Specifies the type of tree to create, either "folder" or "file". Determines the input name and behavior for the generated elements.
 * @param {Array} movingFolderIds - An array of folder IDs (as strings) that should be disabled in the tree because they are in the process of being moved.
 * @return {HTMLElement} An unordered list (ul) HTML element representing the move tree, with nested items and collapsible folders as applicable.
 */
function createMoveTree(data, itemType, movingFolderIds = []) {
    const ul = document.createElement('ul');
    ul.className = 'list-unstyled mb-0';

    if (!["folder", "file"].includes(itemType)) return ul;

    data.forEach(item => {
        const movingFolder = itemType === "folder" && movingFolderIds.includes(item.id?.toString());
        const showChildren = item.children?.length > 0 && !movingFolder;

        const li = document.createElement('li');

        const input = document.createElement('input');
        input.className = 'form-check-input me-2';
        input.type = 'radio';
        input.id = `folder-${item.id}`;
        input.name = itemType === "folder" ? "parent" : "folder";
        input.value = item.id;
        input.required = true;
        input.disabled = movingFolder || (itemType === "folder" && !item.id);

        const icon = document.createElement('i');
        icon.className = 'bi bi-chevron-right me-2 text-muted';
        icon.type = 'button';

        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = input.id;
        label.innerHTML = `<i class="bi bi-folder text-warning me-2"></i> ${item.name}`;

        const ulChildContainer = document.createElement('div');
        if (showChildren) {
            icon.classList.remove('text-muted');
            icon.dataset.bsToggle = 'collapse';
            icon.setAttribute('href', '#collapse-' + item.id);
            icon.role = 'button';

            ulChildContainer.className = 'collapse';
            ulChildContainer.id = 'collapse-' + item.id;

            ulChildContainer.addEventListener('show.bs.collapse', function (event) {
                event.stopPropagation();
                icon.classList.remove('bi-chevron-right');
                icon.classList.add('bi-chevron-down');
            });
            ulChildContainer.addEventListener('hide.bs.collapse', function (event) {
                event.stopPropagation();
                icon.classList.remove('bi-chevron-down');
                icon.classList.add('bi-chevron-right');
            });

            const ulChild = createMoveTree(item.children, itemType, movingFolderIds);
            ulChild.classList.add('ms-4');
            ulChildContainer.appendChild(ulChild);
        }

        li.append(input, icon, label, ulChildContainer);
        ul.appendChild(li);
    });

    return ul;
}

async function fetchResults(url) {
    await drfRequest({
        url: url,
        onSuccess: (data) => {
            const imageList = document.getElementById("image-search-result");
            const imageInfo = document.getElementById("image-search-info");
            const pagination = document.querySelector("#image-search-pagination ul");

            imageList.innerHTML = "";
            pagination.innerHTML = "";

            if (data.results.length === 0) {
                imageInfo.textContent = "No results found.";
                return;
            }

            let currentPage = parseInt(getQueryParam('page', window.location.origin + url));
            if (!currentPage) {
                currentPage = 1;
            }

            if (imageInfo.dataset.pageSize < data.results.length) {
                imageInfo.dataset.pageSize = data.results.length;
            }
            const pageSize = imageInfo.dataset.pageSize;
            const start = (currentPage - 1) * pageSize + 1;
            const end = Math.min(currentPage * pageSize, data.count);
            const totalPages = Math.ceil(data.count / pageSize);

            imageInfo.textContent = `Total: ${data.count} | Showing ${start}-${end} | Page ${currentPage} of ${totalPages}`;

            data.results.forEach(image => {
                const listItem = document.createElement("li");
                listItem.className = "list-group-item d-flex justify-content-between align-items-center";
                listItem.dataset.slideId = image.id;
                listItem.dataset.slideName = image.name;
                listItem.innerHTML = `
                    <div class="d-flex align-items-center">
                        <img src="${image.thumbnail}" height=40 class="me-2" alt="">
                        <a href="${image.view_url}" class="d-inline-block text-truncate text-decoration-none text-body"
                           style="max-width: 200px;" target="_blank" rel="noopener noreferrer nofollow">
                           ${image.name}
                        </a>
                    </div>
                    <div class="btn-group btn-group-sm action-button-group">
                        <a type="button" class="btn btn-outline-warning"
                           href="/images/database/?folder=${image.folder}"
                           target="_blank" rel="noopener noreferrer nofollow">
                           DB
                        </a>
                    </div>
                `;
                imageList.appendChild(listItem);
            });

            // Pagination buttons
            if (data.previous) {
                const prevBtn = document.createElement("li");
                prevBtn.className = "page-item";
                prevBtn.innerHTML = `<a class="page-link" href="#">Previous</a>`;
                prevBtn.addEventListener("click", function (e) {
                    e.preventDefault();
                    fetchResults(data.previous);
                });
                pagination.appendChild(prevBtn);
            }

            if (data.next) {
                const nextBtn = document.createElement("li");
                nextBtn.className = "page-item";
                nextBtn.innerHTML = `<a class="page-link" href="#">Next</a>`;
                nextBtn.addEventListener("click", function (e) {
                    e.preventDefault();
                    fetchResults(data.next);
                });
                pagination.appendChild(nextBtn);
            }
        },
        onError: (error) => {
            showFeedback('Error fetching images: ' + error.message, 'danger');
        }
    });
}

function classifyError(errorData, status) {
    const generalErrors = [];
    const fieldErrors = {};

    if (errorData?.detail) {
        generalErrors.push(errorData.detail);
    }

    if (errorData?.non_field_errors) {
        generalErrors.push(...errorData.non_field_errors);
    }

    Object.entries(errorData || {}).forEach(([key, value]) => {
        if (key !== 'non_field_errors' && key !== 'detail') {
            fieldErrors[key] = Array.isArray(value) ? value.join('\n') : value;
        }
    });

    return {
        message: generalErrors.join('\n') || `Validation error. (Status: ${status})`,
        generalErrors,
        fieldErrors,
    };
}