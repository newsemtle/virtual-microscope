document.addEventListener('DOMContentLoaded', function () {

    document.getElementById('annotation-update-btn')?.addEventListener('click', function (event) {
        const button = event.target;

        const data = {
            // description: document.getElementById('slide-description').value,
            data: anno.getAnnotations(),
        }

        drfRequest({
            url: button.dataset.url,
            method: 'PATCH',
            data: data,
            onSuccess: (data) => {
                annotation.description = data.description;
                annotation.data = data.data;
                showFeedback(`annotation ${data.name} updated successfully!`, "success")
            },
            onError: (error) => {
                showFeedback('Error updating annotation: ' + error.message, "danger");
            }
        })
    });

    document.getElementById('annotation-create-form')?.addEventListener('submit', function (event) {
        event.preventDefault();

        const formData = new FormData(this);

        const data = {
            name: formData.get('name'),
            slide: formData.get('slide'),
            // description: document.getElementById('slide-description').value,
            data: anno.getAnnotations(),
        }

        drfRequest({
            url: this.dataset.url,
            method: 'POST',
            data: data,
            onSuccess: (data) => {
                window.location.replace(window.location.origin + window.location.pathname + `?annotation=${data.id}`);
            },
            onError: (error) => {
                showFeedback('Error creating annotation: ' + error.message, "danger");
            }
        })
    });

});