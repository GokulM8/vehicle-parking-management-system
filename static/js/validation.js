document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector("form");
    if (!form) return;
  
    const inputs = form.querySelectorAll(".field input");
  
    form.addEventListener("submit", (e) => {
      let hasError = false;
  
      inputs.forEach(input => {
        const field = input.closest(".field");
  
        // Remove previous error state
        field.classList.remove("error");
  
        // Check for empty input
        if (input.value.trim() === "") {
          field.classList.add("error");
          hasError = true;
        }
      });
  
      // Prevent form submission if errors exist
      if (hasError) {
        e.preventDefault();
      }
    });
  
  });
  