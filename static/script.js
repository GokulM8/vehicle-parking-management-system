const form = document.querySelector("form"),
emailField = form.querySelector(".email"),
emailInput = emailField.querySelector("input"),
passField = form.querySelector(".password"),
passInput = passField.querySelector("input");

// prevent auto submit
form.onsubmit = (e) => {
  e.preventDefault();

  // Email validation
  if (emailInput.value.trim() === "") {
    emailField.classList.add("shake", "error");
  } else {
    emailField.classList.remove("shake", "error");
  }

  // Password validation
  if (passInput.value.trim() === "") {
    passField.classList.add("shake", "error");
  } else {
    passField.classList.remove("shake", "error");
  }

  setTimeout(() => {
    emailField.classList.remove("shake");
    passField.classList.remove("shake");
  }, 500);

  // ✅ IMPORTANT: submit to Flask only if valid
  if (
    !emailField.classList.contains("error") &&
    !passField.classList.contains("error")
  ) {
    form.submit(); // Flask receives data
  }
};
