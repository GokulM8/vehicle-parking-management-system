document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    let hasError = false;
    const inputs = form.querySelectorAll("input[required]");

    inputs.forEach(input => {
      // Remove previous error styles
      input.classList.remove("border-red-500");
      
      // Check for empty input
      if (input.value.trim() === "") {
        input.classList.add("border-red-500");
        hasError = true;
      }
    });

    // Prevent form submission if errors exist
    if (hasError) {
      e.preventDefault();
      alert("Please fill in all required fields");
    }
  });

  // Real-time validation - remove error styling when user starts typing
  form.querySelectorAll("input[required]").forEach(input => {
    input.addEventListener("input", () => {
      if (input.value.trim() !== "") {
        input.classList.remove("border-red-500");
      }
    });
  });
});
  