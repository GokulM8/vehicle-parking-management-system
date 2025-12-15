const form = document.querySelector("form"),
userField = form.querySelector(".username"),
userInput = userField.querySelector("input"),
emailField = form.querySelector(".email"),
emailInput = emailField.querySelector("input"),
passField = form.querySelector(".password"),
passInput = passField.querySelector("input");

form.onsubmit = (e) => {
  e.preventDefault();

  // Username check
  if (userInput.value.trim() === "") {
    userField.classList.add("shake", "error");
  } else {
    userField.classList.remove("shake", "error");
  }

  // Email check
  if (emailInput.value.trim() === "") {
    emailField.classList.add("shake", "error");
  } else {
    emailField.classList.remove("shake", "error");
  }

  // Password check
  if (passInput.value.trim() === "") {
    passField.classList.add("shake", "error");
  } else {
    passField.classList.remove("shake", "error");
  }

  setTimeout(() => {
    userField.classList.remove("shake");
    emailField.classList.remove("shake");
    passField.classList.remove("shake");
  }, 500);

  // ✅ Submit to Flask only if all valid
  if (
    !userField.classList.contains("error") &&
    !emailField.classList.contains("error") &&
    !passField.classList.contains("error")
  ) {
    form.submit();
  }
};
