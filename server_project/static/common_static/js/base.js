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

const CSRF_TOKEN = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => {
    activateTooltips();

    // localStorage에 저장된 feedback 표시
    let feedbackData = JSON.parse(localStorage.getItem("feedbackData"));
    if (feedbackData && feedbackData.length > 0) {
        feedbackData.forEach(feedback => {
            showFeedback(feedback.text, feedback.type);
        });

        localStorage.removeItem("feedbackData");
    }

    const timeLeftElement = document.getElementById('time-left')
    let lastFetchTime = 0;
    const throttleDuration = 2000;

    timeLeftElement.addEventListener("click", function (event) {
        const now = Date.now();
        if (now - lastFetchTime < throttleDuration) {
            return;
        }
        lastFetchTime = now;

        fetchData({
            url: this.dataset.url,
            method: "POST",
            onSuccess: (data) => {
                startTimer(new Date(data.expire) - Date.now())
            },
            onError: (error) => {
                showFeedback(`Failed to fetch session time: ${error}`, "danger")
            }
        });
    });
    timeLeftElement.click();

    let timer;

    function startTimer(timeInMs) {
        const timeLeftElement = document.getElementById('time-left');

        if (timer) {
            clearInterval(timer);
        }

        function updateTimer() {
            if (timeInMs < 0) {
                clearInterval(interval);
                return;
            }

            const timeLeftInSeconds = Math.floor(timeInMs / 1000);

            const hoursLeft = Math.floor((timeLeftInSeconds % (3600 * 24)) / 3600);
            const minutesLeft = Math.floor((timeLeftInSeconds % 3600) / 60);
            const secondsLeft = Math.floor(timeLeftInSeconds % 60);

            timeLeftElement.textContent = `${hoursLeft.toString().padStart(2, '0')}:${minutesLeft.toString().padStart(2, '0')}:${secondsLeft.toString().padStart(2, '0')}`;

            timeInMs -= 1000;
        }

        updateTimer();
        timer = setInterval(updateTimer, 1000);
    }
});

window.addEventListener("focus", () => {
    if (localStorage.getItem("refreshPage") === "true") {
        localStorage.removeItem("refreshPage");
        location.reload();
    }
});

document.querySelectorAll('.modal').forEach(modalElement => {
    const modal = new bootstrap.Modal(modalElement);

    modalElement.addEventListener('submit', () => {
        modal._config.backdrop = 'static';
        modal._config.keyboard = false;

        modalElement.querySelectorAll('button').forEach(button => {
            button.disabled = true;
        });
    });

    modalElement.addEventListener('hidden.bs.modal', () => {
        modal._config.keyboard = true;
        modal._config.backdrop = true;

        modalElement.querySelectorAll('button').forEach(button => {
            button.disabled = false;
        });

        modalElement.querySelector('form')?.reset();
    });
});

function activateTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-tooltip="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
        new bootstrap.Tooltip(tooltipTriggerEl, {trigger: 'hover', delay: {"show": 500}});
    });
}

/**
 * 메시지를 화면에 표시합니다.
 *
 * @param {String} message - 화면에 표시할 메시지.
 * @param {String} type - 피드백의 종류. "info", "success", "warning", "danger" 중 하나. 기본값은 "info".
 *
 * @example
 * showFeedback("This is an info message", "info");
 * showFeedback("This is a success message", "success");
 * showFeedback("This is a warning message", "warning");
 * showFeedback("This is a danger message", "danger");
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
 * localStorage에 피드백을 저장합니다.
 * 페이지 새로고침 시 localStorage에 저장된 피드백이 표시됩니다.
 *
 * @param {String} message - 화면에 표시할 메시지.
 * @param {String} type - 피드백의 종류. "info", "success", "warning", "danger" 중 하나. 기본값은 "info".
 *
 * @example
 * sendFeedback("This is an info message", "info");
 * sendFeedback("This is a success message", "success");
 * sendFeedback("This is a warning message", "warning");
 * sendFeedback("This is a danger message", "danger");
 */
function sendFeedback(message, type = "info") {
    let feedbackData = JSON.parse(localStorage.getItem("feedbackData")) || [];
    feedbackData.push({text: message, type: type});
    localStorage.setItem("feedbackData", JSON.stringify(feedbackData));
}

/**
 * API 요청을 보내고 응답을 받습니다.
 *
 * @param {Object} options - API 요청 옵션.
 * @param {string} options.url - API 요청 URL.
 * @param {string} [options.method='GET'] - HTTP 메서드.
 * @param {Object} [options.headers={}] - 요청 헤더.
 * @param {Object|string} [options.data=null] - 요청 본문 데이터.
 * @param {Function} [options.onSuccess=() => {}] - API 요청 성공 시 호출될 콜백 함수.
 * @param {Function} [options.onError=() => {}] - API 요청 실패 시 호출될 콜백 함수.
 */
function fetchData({
                       url,
                       method = 'GET',
                       headers = {},
                       data = null,
                       onSuccess = () => {
                       },
                       onError = () => {
                       }
                   }) {
    const options = {method, headers};
    options.headers['X-CSRFToken'] = CSRF_TOKEN;

    if (data) {
        if (data instanceof FormData) {
            options.body = data;
        } else if (typeof data === 'object') {
            // Assume JSON data
            options.body = JSON.stringify(data);
            options.headers['Content-Type'] = 'application/json';
        } else {
            // Assume raw data (string, etc.)
            options.body = data;
        }
    }

    fetch(url, options)
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    let log = 'API Error:'
                    for (let key in errorData) {
                        log += `\n${key}: ${errorData[key]}`;
                    }
                    console.error(log);

                    const uniqueConstraintFailure = Object.values(errorData).some(value =>
                        value.toString().toLowerCase().includes('unique')
                    );

                    if (errorData.detail) {
                        throw new Error(errorData.detail);
                    } else if (uniqueConstraintFailure) {
                        throw new Error('Same name already exists!');
                    } else {
                        throw new Error(`API request failed with status '${response.status} ${response.statusText}'`);
                    }
                });
            } else if (response.status === 204) {
                return null;
            }
            return response.json();
        })
        .then(data => onSuccess(data))
        .catch(error => {
            console.error('Fetch error:', error.message);
            onError(error);
        });
}

/**
 * dictionary 를 전달하면 그에 맞는 `<dl>` (description list) element 의 내부 데이터를 생성합니다.
 *
 * @param {HTMLDListElement} dl - 데이터를 추가할 `<dl>` element.
 * @param {Object} details - 데이터 정보를 담고 있는 key-value 형태의 dictionary.
 * @param {string} details.key - list 항목의 이름.
 * @param {string} details.value - list 항목의 값.
 *
 * @example
 * const dl = document.querySelector('dl');
 * const details = { Name: "John Doe", Age: "30", Occupation: "Engineer" };
 * createDetailList(dl, details);
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

function createTree(data, itemId, type) {
    if (!["folder", "file"].includes(type)) return;

    const ul = document.createElement('ul');
    ul.className = 'list-unstyled';

    data.forEach(item => {
        let selectable = type === "folder" ? item.id.toString() !== itemId : true;
        let showChildren = item.subfolders?.length > 0 && selectable;

        const li = document.createElement('li');

        const input = document.createElement('input');
        input.className = 'form-check-input me-2';
        input.type = 'radio';
        input.id = `folder-${item.id}`;
        input.name = type === "folder" ? "parent" : "folder";
        input.value = item.id;
        input.required = true;
        input.disabled = !selectable;

        const icon = document.createElement('i');
        icon.className = 'bi bi-chevron-right me-2 text-muted';

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

            const ulChild = createTree(item.subfolders, itemId, type);
            ulChild.classList.add('ms-4');
            ulChildContainer.appendChild(ulChild);
        }

        li.append(input, icon, label, ulChildContainer);
        ul.appendChild(li);
    });

    return ul;
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

        fetchData({
            url: button.dataset.urlTree,
            onSuccess: (data) => {
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
                if (itemType === "folder" && !data[0].id) {
                    treeContainer.appendChild(createTree(data[0].subfolders, button.dataset.itemId, itemType));
                } else {
                    treeContainer.appendChild(createTree(data, button.dataset.itemId, itemType));
                }
            },
            onError: (error) => {
                showFeedback('Error fetching folder tree: ' + error.message, 'danger');
            }
        })
    });
}

function submitModalForm(form, method) {
    const contents = form.querySelector('[data-type="contents"]');
    const loading = form.querySelector('[data-type="loading"]');

    contents?.classList.add('d-none');
    loading?.classList.remove('d-none');

    fetchData({
        url: form.dataset.url,
        method: method,
        data: new FormData(form),
        onSuccess: (data) => {
            location.reload();
        },
        onError: (error) => {
            showFeedback(error.message, 'danger');
            $(form).closest('.modal').modal('hide');
        }
    });
}