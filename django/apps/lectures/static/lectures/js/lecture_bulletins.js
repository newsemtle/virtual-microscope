document.addEventListener("DOMContentLoaded", function (event) {

    const lectureItems = document.querySelectorAll(".lecture-item");

    lectureItems.forEach(item => {
        item.addEventListener("click", function (event) {
            const actionEl = event.target.closest("[data-action]");
            if (!actionEl) return;

            const action = actionEl.dataset.action;

            if (action === "hide") {
                event.preventDefault();
                drfRequest({
                    url: API_ROUTES.lectures.detail(actionEl.dataset.lectureId).toggle_status,
                    method: "PATCH",
                    onSuccess: (data) => {
                        hideTooltips(...item.querySelectorAll("[data-bs-tooltip='tooltip']"));
                        item.remove();
                    },
                    onError: (error) => {
                        showFeedback(gettext("Failed to hide the lecture."), "danger");
                    },
                });
            }
        });
    });

});