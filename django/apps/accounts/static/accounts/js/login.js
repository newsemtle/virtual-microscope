document.getElementById("password-toggle").addEventListener("click", function (event) {
    event.preventDefault();
    const input = document.getElementById("password");
    const icon = this.querySelector("i");

    if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("bi-eye-slash");
        icon.classList.add("bi-eye");
    } else {
        input.type = "password";
        icon.classList.remove("bi-eye");
        icon.classList.add("bi-eye-slash");
    }
});

document.getElementById("login-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    submitForm({
        form: this,
        method: "POST",
        onSuccess: (data) => {
            redirectToNextOrDefault("/");
        },
    });
});