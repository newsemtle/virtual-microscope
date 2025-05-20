document.addEventListener("DOMContentLoaded", () => {

    loadFeedback();
    activateTooltips();

    const logoutElement = document.getElementById("logout");
    logoutElement?.addEventListener("click", function (event) {
        drfRequest({
            url: API_ROUTES.accounts.list.logout,
            method: "POST",
            onSuccess: (data) => {
                window.location.href = "/";
            },
            onError: (error) => {
                showFeedback(gettext("Failed to logout."), "danger");
            },
        });
    });

    const sessionTimeElement = document.getElementById("session-time");
    if (sessionTimeElement) {
        let timer = new Timer("session-time");
        let lastFetchTime = 0;
        const throttleDuration = 2000;
        sessionTimeElement.addEventListener("click", function (event) {
            const now = Date.now();
            if (now - lastFetchTime < throttleDuration) {
                return;
            }
            lastFetchTime = now;
            drfRequest({
                url: API_ROUTES.accounts.list.session_extend,
                method: "POST",
                onSuccess: (data) => {
                    timer.start(new Date(data.expire) - Date.now());
                },
                onError: (error) => {
                    showFeedback(gettext("Failed to get session time."), "danger");
                },
            });
        });
        sessionTimeElement.click();
    }

    document.querySelectorAll(".modal")?.forEach(modalElement => {
        modalElement.addEventListener("hidden.bs.modal", () => {
            unfreezeModal(modalElement);
            const forms = modalElement.querySelectorAll("form");
            [...forms].forEach(form => {
                form.reset();
                clearFormErrors(form);
            });
        });
    });

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
            const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
            const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
            const s = String(seconds % 60).padStart(2, "0");

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
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function redirectToNextOrDefault(defaultUrl) {
    const next = getQueryParam("next");
    if (next && next.startsWith("/")) {
        window.location.href = next;
    } else if (defaultUrl.startsWith("/")) {
        window.location.href = defaultUrl;
    } else {
        window.location.href = "/";
    }
}

function getQueryParam(key, url = window.location.href) {
    const searchParams = new URL(url).searchParams;
    return searchParams.get(key);
}

function formatDate(date_string) {
    const date = new Date(date_string);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    const seconds = date.getSeconds().toString().padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

function truncateString(str, maxLength) {
    return str.length > maxLength ? str.slice(0, maxLength) + "..." : str;
}

function activateTooltips(...elementList) {
    let tooltipTriggerList;
    if (elementList.length > 0) {
        tooltipTriggerList = elementList;
    } else {
        tooltipTriggerList = document.querySelectorAll("[data-bs-tooltip='true']");
    }
    [...tooltipTriggerList].forEach(tooltipTriggerEl => {
        // Create tooltip if not already present
        bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl, {
            trigger: "hover",
            delay: {show: 1000},
        });
    });
}

function hideTooltips(...elementList) {
    let tooltipHideList;
    if (elementList.length > 0) {
        tooltipHideList = elementList;
    } else {
        tooltipHideList = document.querySelectorAll("[data-bs-tooltip='true']");
    }
    [...tooltipHideList].forEach(tooltipTriggerEl => {
        bootstrap.Tooltip.getInstance(tooltipTriggerEl)?.hide();
    });
}

function freezeModal(modalElement) {
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal._config.keyboard = false;
    modal._config.backdrop = "static";

    modalElement.querySelectorAll("button").forEach(button => {
        button.disabled = true;
    });
}

function unfreezeModal(modalElement) {
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal._config.keyboard = true;
    modal._config.backdrop = true;

    modalElement.querySelectorAll("button").forEach(button => {
        button.disabled = false;
    });
}

function classifyError(errorData) {
    const generalErrors = [];
    const fieldErrors = {};

    if (errorData?.detail) {
        generalErrors.push(errorData.detail);
    }

    if (errorData?.non_field_errors) {
        generalErrors.push(...errorData.non_field_errors);
    }

    Object.entries(errorData || {}).forEach(([key, value]) => {
        if (key !== "non_field_errors" && key !== "detail") {
            fieldErrors[key] = Array.isArray(value) ? value.join("\n") : value;
        }
    });

    return {
        message: generalErrors.join("\n") || "Validation error",
        generalErrors,
        fieldErrors,
    };
}

function handleFormErrors(form, error) {
    clearFormErrors(form);

    const message = form.querySelector(`[data-type="message"]`);
    if (message) {
        message.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${error.message}`;
        message.classList.remove("d-none");
    }

    if (error.fieldErrors) {
        for (const [field, message] of Object.entries(error.fieldErrors)) {
            const input = form.querySelector(`[name='${field}']`);
            if (input) {
                input.classList.add("is-invalid");
            }
            const feedback = form.querySelector(`#${field}-feedback`);
            if (feedback) {
                feedback.textContent = message;
            }
        }
    }
}

function clearFormErrors(formElement) {
    formElement.classList.remove("was-validated");
    formElement.querySelectorAll(".is-invalid").forEach((input) => {
        input.classList.remove("is-invalid");
    });
    formElement.querySelectorAll(".invalid-feedback").forEach((feedback) => {
        feedback.textContent = "";
    });
    formElement.querySelectorAll("[data-type='message']").forEach((message) => {
        message.classList.add("d-none");
        message.innerHTML = "";
    });
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
    }, 3000); // display for 3 seconds
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
 * Loads feedback data from local storage, displays it using the `showFeedback` method,
 * and then removes the feedback data from local storage.
 *
 * @return {void} This method does not return a value.
 */
function loadFeedback() {
    let feedbackData = JSON.parse(localStorage.getItem("feedbackData"));
    if (feedbackData && feedbackData.length > 0) {
        feedbackData.forEach(feedback => {
            showFeedback(feedback.text, feedback.type);
        });
        localStorage.removeItem("feedbackData");
    }
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
                              method = "GET",
                              headers = {},
                              data = null,
                              onSuccess = () => {
                              },
                              onError = () => {
                              },
                              onNext: onFinally = () => {
                              },
                          }) {
    const options = {method, headers};
    options.headers["X-CSRFToken"] = getCookie("csrftoken");
    options.headers["Accept-Language"] = navigator.language;

    if (data) {
        if (data instanceof FormData) {
            if ([...data.entries()].length !== 0) {
                options.body = data;
            }
        } else if (typeof data === "object") {
            options.body = JSON.stringify(data);
            options.headers["Content-Type"] = "application/json";
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
                    errorData = {detail: "Invalid response"};
                }

                const classified = classifyError(errorData);
                throw {...classified, status, raw: errorData};
            }

            return status === 204 ? null : response.json();
        })
        .then(data => onSuccess(data))
        .catch(error => {
            console.error(error);
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
                        },
                    }) {
    if (form.checkValidity()) {
        form.classList.remove("was-validated");
    } else {
        form.classList.add("was-validated");
        form.querySelector("[data-type='message']").classList.add("d-none");
        form.querySelectorAll(".invalid-feedback").forEach((feedback) => {
            feedback.textContent = gettext("This field is required.");
        });
        onError({message: "Validation error"});
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
        },
    });
}

/**
 * Populates a definition list (dl element) with the provided details.
 *
 * @param {HTMLDListElement} dl - The definition list element to populate.
 * @param {Map<string, string|HTMLElement|Map>} details - A map containing field names as keys and values as the corresponding content. Values can be strings, HTML elements, or nested maps for hierarchical data.
 * @return {void} This function does not return a value.
 */
function populateDetailList(dl, details) {
    for (const [field, content] of details) {
        const dt = document.createElement("dt");
        dt.className = "col-sm-3 mb-2";
        dt.textContent = field;

        const dd = document.createElement("dd");
        dd.className = "col-sm-9";

        if (content instanceof Map) {
            const nestedDl = document.createElement("dl");
            nestedDl.className = "row";
            populateDetailList(nestedDl, content);
            dd.appendChild(nestedDl);
        } else if (content instanceof HTMLElement) {
            dd.appendChild(content);
        } else {
            dd.textContent = content;
        }

        dl.append(dt, dd);
    }
}

async function fetchImageSearchResults(url) {
    await drfRequest({
        url: url,
        onSuccess: (data) => {
            const imageList = document.getElementById("image-search-result");
            const imageInfo = document.getElementById("image-search-info");
            const pagination = document.querySelector("#image-search-pagination ul");

            imageList.innerHTML = "";
            pagination.innerHTML = "";

            if (data.results.length === 0) {
                imageInfo.textContent = gettext("No results found.");
                return;
            }

            let currentPage = parseInt(getQueryParam("page", window.location.origin + url), 10);
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

            imageInfo.textContent = interpolate(gettext("Total: %(count)s | Showing %(start)s-%(end)s | Page %(currentPage)s of %(totalPages)s"), {
                count: data.count,
                start,
                end,
                currentPage,
                totalPages,
            }, true);

            data.results.forEach(image => {
                const listItem = document.createElement("li");
                listItem.className = "list-group-item d-flex justify-content-between align-items-center";
                listItem.dataset.slideId = image.id;
                listItem.dataset.slideName = image.name;

                const title = document.createElement("div");
                title.className = "d-flex align-items-center";

                const titleImg = document.createElement("img");
                titleImg.src = image.thumbnail;
                titleImg.height = 40;
                titleImg.className = "me-2";
                titleImg.alt = "";

                const titleText = document.createElement("a");
                titleText.className = "d-inline-block text-truncate text-decoration-none text-body";
                titleText.href = `/viewer/${image.id}/`;
                titleText.textContent = image.name;
                titleText.target = "_blank";
                titleText.rel = "noopener noreferrer nofollow";

                const btnGroup = document.createElement("div");
                btnGroup.className = "btn-group btn-group-sm action-button-group";

                const dbBtn = document.createElement("a");
                dbBtn.className = "btn btn-outline-warning";
                dbBtn.href = `/images/database/?folder=${image.folder}`;
                dbBtn.textContent = "DB";
                dbBtn.title = gettext("Open in DB");
                dbBtn.dataset.bsTooltip = "true";
                dbBtn.target = "_blank";
                dbBtn.rel = "noopener noreferrer nofollow";

                title.append(titleImg, titleText);
                btnGroup.appendChild(dbBtn);
                listItem.append(title, btnGroup);
                imageList.appendChild(listItem);

                activateTooltips(...listItem.querySelectorAll("[data-bs-tooltip='true']"));
            });

            // Pagination buttons
            if (data.previous) {
                const prevBtn = document.createElement("li");
                prevBtn.className = "page-item";
                prevBtn.innerHTML = `<a class="page-link" href="#">Previous</a>`;
                prevBtn.addEventListener("click", function (e) {
                    e.preventDefault();
                    fetchImageSearchResults(data.previous);
                });
                pagination.appendChild(prevBtn);
            }

            if (data.next) {
                const nextBtn = document.createElement("li");
                nextBtn.className = "page-item";
                nextBtn.innerHTML = `<a class="page-link" href="#">Next</a>`;
                nextBtn.addEventListener("click", function (e) {
                    e.preventDefault();
                    fetchImageSearchResults(data.next);
                });
                pagination.appendChild(nextBtn);
            }
        },
        onError: (error) => {
            showFeedback(gettext("Failed to get results."), "danger");
        },
    });
}